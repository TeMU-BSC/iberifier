from mongo_utils import mongo_utils
import yaml
import argparse
import itertools
import logging
import os
import re
import string
import sys
from datetime import datetime, timedelta

from bs4 import BeautifulSoup
# from collections import OrderedDict
from language_detector import detect_language
from transformers import pipeline

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


def detect_lang(txt):
    lang_dect = detect_language(txt)
    return lang_dect["pref_lang"]


def text_from_facts(db, collection, args):
    search = {}
    if not args.rerun:
        search["keyword_pairs"] = {"$exists": False}
    if args.time_window:
        today = datetime.today()
        days_ago = today - timedelta(days=args.time_window)
        search["date"] = {'$gt': days_ago, '$lt': today}
    if collection == "maldita":
        logger.info('Searching in maldita for:', search)
        return parsing_new_fact_maldita(db, collection, search)
    elif collection == "google":
        logger.info('Searching in google for:', search)
        return parsing_new_fact_google(db, collection, search)
    else:
        raise Exception("Not the right collection")


def remove_nonalpha(strings):
    new = []
    for s in strings:
        new.append(''.join(x for x in s if x.isalpha()))
    new = list(set([n for n in new if n != '']))
    return new


def entity_extraction(nlp, text):
    return_entity = dict()
    for ent in nlp(text):
        return_entity.setdefault(ent["entity_group"], set()).add(
            clean_word(ent["word"])
        )
    for result in return_entity:
        return_entity[result] = list(return_entity[result])
    return return_entity


def remove_compiled_regex(txt: str, compiled_regex: re.compile, substitute: str = ""):
    """
    Search for the compiled regex in the txt and either replace it with the substitute or remove it
    """
    entities = compiled_regex.findall(txt)
    txt = compiled_regex.sub(substitute, txt)
    return txt, entities


def extract_url(txt):
    url_re = re.compile(
        "http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+")
    txt, urls = remove_compiled_regex(txt=txt, compiled_regex=url_re)
    return txt, urls



def text_from_facts(db, collection, args):
    search = {}
    if not args.rerun:
        search["keyword_pairs"] = {"$exists": False}
    if args.time_window:
        today = datetime.today()
        days_ago = today - timedelta(days=args.time_window)
        search["date"] = {'$gt': days_ago, '$lt': today}
    if collection == "maldita":
        logger.info('Searching in maldita for:', search)
        return parsing_new_fact_maldita(db, collection, search)
    elif collection == "google":
        logger.info('Searching in google for:', search)
        return parsing_new_fact_google(db, collection, search)
    else:
        raise Exception("Not the right collection")


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


def load_all_mdels(dict_models):
    dict_model_loaded = dict()
    for task in dict_models:
        for lang in dict_models[task]:
            model = _load_nlp_model(task, lang, dict_models[task][lang])
            dict_model_loaded[f'{task}_{lang}'] = model
    return dict_model_loaded


def get_list_to_update(db, collections, ner_key, pos_key, rerun, time_window):
    search = {}

    if rerun:
        search[ner_key] = {"$exists": False}

    for col in collections:

        cursor = db[col].find(search, batch_size=1)
        for record in cursor:
            fact_id = record["_id"]
            text = record["text"]
            content = record["claimReview"][0]["title"]
            lang = record["claimReview"][0]["languageCode"]
            yield fact_id, text, content, lang
        cursor.close()


def parsing_new_fact_google(db, collection, search):
    cursor = db[collection].find(search, batch_size=1)
    for record in cursor:
        fact_id = record["_id"]
        claim = record["text"]
        check = record["claimReview"][0]["title"]
        lang = record["claimReview"][0]["languageCode"]
        yield fact_id, claim, check, lang
    cursor.close()


def parsing_new_fact_maldita(db, collection, search):
    cursor = db[collection].find(search)
    for record in cursor:
        # print(record)
        fact_id = record["_id"]
        text = record["text"]
        try:
            content = BeautifulSoup(record["content"], "lxml").text
        except TypeError:  # Maybe empty
            content = None

        print(text)
        yield fact_id, text, content, None
    cursor.close()


def main():

    # DB Connection
    logger.info("Connecting to the db")
    db = mongo_utils.get_mongo_db()
    logger.info("Connected to: {}".format(db))

    dict_models = config_all['ent_extraction_params']['language_models']
    rerun = config_all['ent_extraction_params']['rerum']
    ner_key = config_all['ent_extraction_params']['ner_key']
    pos_key = config_all['ent_extraction_params']['pos_key']
    time_window = config_all['ent_extraction_params']['time_window']
    dict_loaded_models = load_all_mdels(dict_models)
    collections = ['maldita', 'google']

    list_fact_to_update = get_list_to_update(db, collections,
                                             ner_key, pos_key, rerun, time_window)
    for claim in list_fact_to_update:
        if claim['lang'] is None:
            lang = detect_lang(claim['text'])
        else:
            lang = claim['lang']
        if lang in ['es', 'ca', 'pt']:
            ner_model = select_model('ner', lang, dict_loaded_models)
            ner_model = select_model('pos', lang, dict_loaded_models)

            # text, urls_extracted = extract_url(text)
