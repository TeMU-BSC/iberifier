import yaml
import argparse
import itertools
import logging
import os
import re
import string
import sys
from datetime import datetime, timedelta
import logging.config
import tqdm

from bs4 import BeautifulSoup
# from collections import OrderedDict
from language_detector import detect_language
from transformers import pipeline

from mongo_utils import mongo_utils
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

config_path = os.path.join(os.path.dirname(
    __file__), '../config', 'config.yaml')
config_all = yaml.safe_load(open(config_path))

logging_config_path = os.path.join(os.path.dirname(
    __file__), '../config', config_all['logging']['logging_filename'])
with open(logging_config_path,  "r") as f:
    yaml_config = yaml.safe_load(f.read())
    logging.config.dictConfig(yaml_config)

logger = logging.getLogger(config_all['logging']['level'])


def update_fact(
    db,
    collection,
    fact_id,
    url,
    **kwargs
):
    to_update = {k: kwargs[k] for k in kwargs if kwargs[k]}
    db[collection].update_one(
        {"fact_id": fact_id, 'url_fact': url},
        {"$set": to_update},
        upsert=True
    )
    # db[collection].insert_one(to_update)


def get_words_from_model(model, text):
    def cleaning_word(word):
        word = re.sub(r"[^ \nA-Za-z0-9À-ÖØ-öø-ÿЀ-ӿ/]+", "", word)
        return word.strip().lower().translate(str.maketrans("", "", string.punctuation))

    return_entity = dict()

    for ent in model(text):
        word = cleaning_word(ent['word'])
        if word:
            return_entity.setdefault(ent["entity_group"], set()).add(word)
    for result in return_entity:
        return_entity[result] = list(return_entity[result])
    return return_entity


def select_model(task, lang, models):
    return models[task][lang]


def _load_nlp_model(task, lang, model):
    logger.info("Load {} {} model: {}".format(
        lang, task, model))
    nlp_model = pipeline(
        ("token-classification" if task == "pos" else task),
        model=model,
        tokenizer=model,
        aggregation_strategy="max",
    )
    return nlp_model


def load_all_models(dict_models):
    dict_model_loaded = dict()
    for task in dict_models:
        dict_model_loaded[task] = dict()
        for lang in dict_models[task]:
            model = _load_nlp_model(task, lang, dict_models[task][lang])
            dict_model_loaded[task][lang] = model
    return dict_model_loaded


def remove_compiled_regex(txt: str, compiled_regex: re.compile, substitute: str = ""):
    """
    Search for the compiled regex in the txt and either replace it with the substitute or remove it
    """
    entities = compiled_regex.findall(txt)
    txt = compiled_regex.sub(substitute, txt)
    return txt, entities


def extract_url(txt, url_re):
    txt, urls = remove_compiled_regex(txt=txt, compiled_regex=url_re)
    return txt, urls


def _remove_tags(txt):
    try:
        return BeautifulSoup(txt, "lxml").text
    except TypeError:  # Maybe empty
        return None
    # return txt


def _get_val_from_dot(dct, string):
    keys = string.split('.')
    v = dct
    for key in keys:
        v = v[key]
    return v


def _getting_info(record, text_field):
    info = {'fact_id': record['_id']}
    for k in text_field:
        info[k] = _get_val_from_dot(record, text_field[k])
    info['claim'] = _remove_tags(info['claim'])
    info['review'] = _remove_tags(info['review'])
    return info


def get_list_to_update(db, col, col_keyword):
    aggregate_query = [
        {
            "$lookup": {
                'from': col_keyword,
                "localField": "_id",
                "foreignField": "fact_id",
                "as": "join"
            }
        },
        {
            "$match": {
                "join": {
                    "$size": 0
                }
            }
        },
        {
            "$project": {
                # "join": 0,
                "_id": 1
            }
        }
    ]
    return [i['_id'] for i in db[col].aggregate(aggregate_query)]


def get_documents(db, col_factcheck, col_keyword, field):
    list_ids = get_list_to_update(db, col_factcheck, col_keyword)
    tqdm_length = len(list_ids)
    cursor = db[col_factcheck].find({'_id': {"$in": list_ids}}, batch_size=1)

    for record in tqdm.tqdm(cursor, total=tqdm_length):
        yield _getting_info(
            record, text_field=field)
    cursor.close()


# FIXME: Assumed so far but should be inferred as before
def assign_lang(reviewer):
    if reviewer in ['Maldita.es', 'EFE Verifica', 'Verificat', 'Newtral']:
        return 'es'
    elif reviewer in ['Poligrapho']:
        return 'pt'
    else:
        return None


def main():

    # DB Connection
    logger.info("Connecting to the db")
    db = mongo_utils.get_mongo_db()
    logger.info("Connected to: {}".format(db))

    col_keywords = config_all['mongodb_params']['keywords']['name']

    dict_models = config_all['ent_extraction_params']['language_models']

    maldita_fields = config_all['api_maldita_params']['fields']
    google_fields = config_all['api_google_params']['fields']
    fields = {'maldita': {k: maldita_fields[k] for k in maldita_fields},
              'google': {k: google_fields[k] for k in google_fields}}

    url_re = re.compile(
        "http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+")

    dict_loaded_models = load_all_models(dict_models)
    logger.debug(dict_loaded_models)
    for col in ['maldita', 'google']:
        logger.info(f'{col}: NER & POS')
        for info in get_documents(db, col, col_keywords, fields[col]):

            fact_id = info['fact_id']
            url = info['url']
            date = info['date']

            try:
                reviewer = info['reviewer']
            except KeyError:
                reviewer = None
            try:
                lang = info['lang']
            except KeyError:
                try:
                    # lang = detect_language(claim + ' ' + review)
                    lang = assign_lang(reviewer)
                except TypeError:
                    lang = None

            if lang in ['es', 'ca', 'pt']:
                ner_model = select_model('ner', lang, dict_loaded_models)
                pos_model = select_model('pos', lang, dict_loaded_models)

                try:
                    claim, urls_claim = extract_url(info['claim'], url_re)
                except (KeyError, TypeError):
                    claim = urls_claim = None

                if claim:
                    ner_claim = get_words_from_model(ner_model, claim)
                    pos_claim = get_words_from_model(pos_model, claim)
                else:
                    ner_claim = pos_claim = None

                try:
                    review, urls_review = extract_url(info['review'], url_re)
                except (KeyError, TypeError):
                    review = urls_review = None

                if review:
                    ner_review = get_words_from_model(ner_model, review)
                    pos_review = get_words_from_model(pos_model, review)
                else:
                    ner_review = pos_review = None

                update_fact(
                    db,
                    col_keywords,
                    fact_id,
                    url,
                    date=date,
                    claim=claim,
                    urls_claim=urls_claim,
                    ner_claim=ner_claim,
                    pos_claim=pos_claim,
                    review=review,
                    urls_review=urls_review,
                    ner_review=ner_review,
                    pos_review=pos_review)


if __name__ == "__main__":
    main()
