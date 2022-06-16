from genericpath import commonprefix
import re
from bs4 import BeautifulSoup
import string

import itertools
from datetime import datetime
from collections import OrderedDict
from language_detector import detect_language

from transformers import AutoTokenizer, AutoModelForTokenClassification
from transformers import pipeline

import sys,os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from mongo_utils import mongo_utils

## Setting up to rerun or not (True/False)
RERUN = True

# Logging options
import logging

logger_level = "DEBUG"
stream_level = "INFO"
file_level = "ERROR"

logger = logging.getLogger(__name__)
logger_set_level = getattr(logging, logger_level)
logger.setLevel(logger_set_level)
formatter = logging.Formatter("%(asctime)s :: %(levelname)s :: %(name)s :: %(message)s")

stream_handler = logging.StreamHandler()
stream_set_level = getattr(logging, stream_level)
stream_handler.setLevel(stream_set_level)
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)


def update_fact(db, collection, fact_id, result_ner, result_pos, lang, urls, bigrams):
    db[collection].update_one(
        {"_id": fact_id},
        {
            "$set": {
                "NER": result_ner,
                "POS": result_pos,
                "LANG": lang,
                "URLS": urls,
                "bigrams": bigrams,
            }
        },
    )


def check_cooccurrency(keywords, db, col_dict):
    return bool(db[col_dict].find_one({"words": {"$all": list(keywords)}}, {"_id": 0}))


def delete_from_cooccurrency(keywords_list, db, col_dict):
    try:
        for pairs in list(
            keywords_list
        ):  # Need to create a copy of it to delete while looping
            if check_cooccurrency(pairs, db, col_dict):
                keywords_list.remove(pairs)
        return keywords_list
    except TypeError:  # Empty list
        raise Exception(
            "Issue with removing words from cooccurrency, probably empty list of keywords"
        )


def create_bigrams(db, col_dict, ner_ent=None, pos_ent=None):
    def pairwise(iterable):
        a, b = itertools.tee(iterable)
        next(b, None)
        return zip(a, b)

    ner_words = list()
    pos_words = list()
    keywords_list = list()

    if ner_ent:
        for key in ner_ent:
            ner_words = ner_words + ner_ent[key]
        ner_words = list(set(ner_words))  # Sometimes same entity appears several times
        # In case the list is at least two words
        if len(ner_words) >= 2:
            keywords_list = sorted(list(pairwise(ner_words)))
            keywords_list = delete_from_cooccurrency(keywords_list, db, col_dict)
            # keywords_list = list(itertools.permutations(ner_words, 2))
            # Again, checking if the resulting list without the cooccurrencies is still >=2
            if len(keywords_list) >= 2:
                return keywords_list

    if pos_ent:
        for key in pos_ent:
            if key in ["NOUN", "ADJ"]:
                pos_words = pos_words + pos_ent[key]
        # print("POS WORDS: {}".format(pos_words))
        full_list = sorted(
            ner_words + pos_words
        )  # Sometimes same entity appears several times

        keywords_list = sorted(list(pairwise(full_list)))
        keywords_list = delete_from_cooccurrency(keywords_list, db, col_dict)
        return keywords_list


def clean_word(word):
    return word.strip().lower().translate(str.maketrans("", "", string.punctuation))


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


def extract_url(txt, compiled_url_regex):
    txt, urls = remove_compiled_regex(txt=txt, compiled_regex=compiled_url_regex)
    return txt, urls


def select_model(lang, model_es, model_pt, model_cat):
    if lang == "es":
        return model_es
    elif lang == "pt":
        return model_pt
    elif lang == "ca":
        return model_cat
    else:
        pass


def detect_lang(txt):
    lang_dect = detect_language(txt)
    return lang_dect["pref_lang"]


def parsing_new_fact_maldita(db, collection, search):
    for record in db[collection].find(search):
        fact_id = record["_id"]
        try:
            clean_content = BeautifulSoup(record["content"], "lxml").text
            text = record["text"] + " " + clean_content
        except TypeError:  # Maybe empty
            text = record["text"]

        yield fact_id, text, None


def parsing_new_fact_google(db, collection, search):
    for record in db[collection].find(search):
        fact_id = record["_id"]
        text = record['title'] + ' ' + record['text']
        lang = record['claimReview.languageCode']
        yield fact_id, text, lang



def text_from_facts(db=None, collection=None, rerun=None):
    if rerun is False:
        search = {"bigrams": {"$exists": False}}
    else:
        search = {}
    if collection == 'col_maldita':
        return parsing_new_fact_maldita(db, collection, search)
    elif collection == 'google':
        return parsing_new_fact_google(db, collection, search)
    else:
        raise Exception(
            "Not the right collection"
        )


def main():

    ## DB Connection
    logger.info("Connecting to the db")
    db = mongo_utils.get_mongo_db()

    logger.info("Connected to: {}".format(db))
    # col_maldita = "maldita"
    # col_google = 'google'
    col_cooccurence = "cooccurrence"

    # Regex for URL extraction
    url_re = re.compile(
        "http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+"
    )

    # Load models

    ## ES MODEL FROM TEMU
    # TODO the aggregation_strategy raises a warning because it is not
    # implemented, while the doc says it is
    # https://huggingface.co/PlanTL-GOB-ES/roberta-base-bne-capitel-ner-plus/blob/main/README.md
    model_location_ner_es = "./models/roberta-base-bne-capitel-ner-plus/"
    nlp_ner_es = pipeline(
        "ner",
        model=model_location_ner_es,
        tokenizer=model_location_ner_es,
        aggregation_strategy="simple",
    )
    logger.info("Load ES NER model: {}".format(model_location_ner_es))
    # nlp_ner_es= pipeline("ner", model=model_name_ner_es, aggregation_strategy="first")

    model_name_pos_es = "PlanTL-GOB-ES/roberta-base-bne-capitel-pos"
    logger.info("Load ES POS model: {}".format(model_name_pos_es))
    nlp_pos_es = pipeline("ner", model=model_name_pos_es, aggregation_strategy="simple")

    ## CAT MODEL FROM TEMU
    model_name_ner_cat = "projecte-aina/roberta-base-ca-cased-ner"
    logger.info("Load CAT NER model: {}".format(model_name_ner_cat))
    nlp_ner_cat = pipeline(
        "ner", model=model_name_ner_cat, aggregation_strategy="simple"
    )

    model_name_pos_cat = "projecte-aina/roberta-base-ca-cased-pos"
    logger.info("Load CAT POS model: {}".format(model_name_pos_cat))
    nlp_pos_cat = pipeline(
        "ner", model=model_name_pos_cat, aggregation_strategy="simple"
    )

    ## PT Model from:
    model_name_ner_pt = "monilouise/ner_news_portuguese"
    logger.info("Load PT NER model: {}".format(model_name_ner_pt))
    nlp_ner_pt = pipeline("ner", model=model_name_ner_pt, aggregation_strategy="simple")

    model_name_pos_pt = "PT_MODEL"
    logger.info("Load PT POS model: {}".format(model_name_pos_pt))
    nlp_pos_pt = None
    logger.info("Model loaded")

    ## Running
    for col_to_parse in ['maldita', 'google']:
        for fact_id, text, lang in text_from_facts(db, col_to_parse, rerun=RERUN):
            if lang is None:
                lang = detect_lang(text)
            if lang in ["es", "ca", "pt"]:
                ner_model = select_model(lang, nlp_ner_es, nlp_ner_pt, nlp_ner_cat)
                pos_model = select_model(lang, nlp_pos_es, nlp_pos_pt, nlp_pos_cat)
                result_ner = None
                result_pos = None
                text, urls_extracted = extract_url(text, url_re)
                print(lang)
                print(text)
                result_ner = entity_extraction(ner_model, text)
                print("NER: {}".format(result_ner))
                if lang == "es" or lang == "ca":
                    result_pos = entity_extraction(pos_model, text)
                    print("POS: {}".format(result_pos))
                bigrams = create_bigrams(
                    db, col_cooccurence, ner_ent=result_ner, pos_ent=result_pos
                )
                update_fact(
                    db,
                    col_to_parse,
                    fact_id,
                    result_ner,
                    result_pos,
                    lang,
                    urls_extracted,
                    bigrams,
                )


if __name__ == "__main__":
    main()
