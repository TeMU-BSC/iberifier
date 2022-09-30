#from genericpath import commonprefix
import re
from bs4 import BeautifulSoup
import string

import itertools
from datetime import datetime, timedelta
#from collections import OrderedDict
from language_detector import detect_language

#from transformers import AutoTokenizer, AutoModelForTokenClassification
from transformers import pipeline

import sys, os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from mongo_utils import mongo_utils

## Setting up to rerun or not (True/False)
RERUN = False

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


def update_fact(
    db,
    collection,
    fact_id,
    result_ner,
    result_pos,
    lang,
    urls,
    bigrams,
    trigrams,
    fourgrams,
):
    db[collection].update_one(
        {"_id": fact_id},
        {
            "$set": {
                "NER": result_ner,
                "POS": result_pos,
                "LANG": lang,
                "URLS": urls,
                "bigrams": bigrams,
                "trigrams": trigrams,
                "fourgrams": fourgrams,
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


def create_keyword_list(ner_ent=None, pos_ent=None):
    ner_words = list()
    pos_words = list()

    if ner_ent:
        for key in ner_ent:
            ner_words = ner_words + ner_ent[key]
        ner_words = list(set(ner_words))  # Sometimes same entity appears several times

        # In case the list is at least two words
        if len(ner_words) >= 3:
            return ner_words

    if pos_ent:
        for key in pos_ent:
            if key in ["NOUN", "ADJ"]:
                pos_words = pos_words + pos_ent[key]
        # print("POS WORDS: {}".format(pos_words))
        full_list = sorted(
            ner_words + pos_words
        )  # Sometimes same entity appears several times

        return full_list
    return []


def create_bigrams(db, col_dict, keywords_list):
    combinations = itertools.combinations(keywords_list, 2)
    bigrams = sorted(list(combinations))
    bigrams = delete_from_cooccurrency(bigrams, db, col_dict)
    return bigrams


def create_xgrams(keywords_list, x=3):
    combinations = itertools.combinations(keywords_list, x)
    xgrams = sorted(list(combinations))
    # TODO delete coocurrency if possible
    return xgrams


def clean_word(word):
    word = re.sub(r"[^ \nA-Za-z0-9À-ÖØ-öø-ÿЀ-ӿ/]+", "", word)
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
    cursor = db[collection].find(search) # TODO: it has to find the ones from the indicated date, not any random
    print('it does get here')
    print(search)
    for record in cursor:
        print(record)
        fact_id = record["_id"]
        try:
            clean_content = BeautifulSoup(record["content"], "lxml").text
            text = record["text"] + " " + clean_content
        except TypeError:  # Maybe empty
            text = record["text"]

        yield fact_id, text, None
    cursor.close()


def parsing_new_fact_google(db, collection, search):
    cursor = db[collection].find(search, batch_size=1)
    for record in cursor:
        fact_id = record["_id"]
        text = record["claimReview"][0]["title"] + " " + record["text"]
        lang = record["claimReview"][0]["languageCode"]
        yield fact_id, text, lang
    cursor.close()


def text_from_facts(db=None, collection=None, rerun=None):
    today = datetime.today()
    days_ago = today - timedelta(days=3) # TODO: this should be changed to the frequency of the execution
    if rerun is False:
        search = {"bigrams": {"$exists": False}, "date":{'$gt': days_ago, '$lt': today}}
    else:
        search = {"date":{'$gt': days_ago, '$lt': today}}
    if collection == "maldita":
        return parsing_new_fact_maldita(db, collection, search)
    elif collection == "google":
        return parsing_new_fact_google(db, collection, search)
    else:
        raise Exception("Not the right collection")

def load_model(path, task, lang):
    logger.info("Load {} {} model: {}".format(lang, task, path))
    nlp_ner_es = pipeline(
        ("ner" if task=="pos" else task),
        model=path,
        tokenizer=path,
        aggregation_strategy="simple",
    )
    return nlp_ner_es

def main():

    ## DB Connection
    logger.info("Connecting to the db")
    db = mongo_utils.get_mongo_db()
    logger.info("Connected to: {}".format(db))
    col_cooccurence = "cooccurrence"

    # Regex for URL extraction
    url_re = re.compile("http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+")

    # Load models
    # TODO the aggregation_strategy raises a warning because it is not
    # TODO: models should only be loaded when they are needed right now it takes forever
    # implemented, while the doc says it is
    # https://huggingface.co/PlanTL-GOB-ES/roberta-base-bne-capitel-ner-plus/blob/main/README.md
    nlp_ner_es = load_model("PlanTL-GOB-ES/roberta-base-bne-capitel-ner-plus", "ner", "ES")
    nlp_pos_es = load_model("PlanTL-GOB-ES/roberta-base-bne-capitel-pos", "pos", "ES")
    nlp_ner_cat = load_model("projecte-aina/roberta-base-ca-cased-ner", "ner", "CAT")
    nlp_pos_cat = load_model("projecte-aina/roberta-base-ca-cased-pos", "pos", "CAT")
    nlp_ner_pt = load_model("monilouise/ner_news_portuguese", "ner", "PT")
    nlp_pos_pt = None # we don't have one currently

    ## Running
    for col_to_parse in ["maldita", "google"]:
        for fact_id, text, lang in text_from_facts(db, col_to_parse, rerun=RERUN):
            if lang is None:
                lang = detect_lang(text)
            if lang in ["es", "ca", "pt"]:
                ner_model = select_model(lang, nlp_ner_es, nlp_ner_pt, nlp_ner_cat) # TODO: this is not efficient
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
                keywords = create_keyword_list(ner_ent=result_ner, pos_ent=result_pos)
                bigrams = create_bigrams(db, col_cooccurence, keywords)
                trigrams = create_xgrams(keywords, 3)
                fourgrams = create_xgrams(keywords, 4)

                update_fact(
                    db,
                    col_to_parse,
                    fact_id,
                    result_ner,
                    result_pos,
                    lang,
                    urls_extracted,
                    bigrams,
                    trigrams,
                    fourgrams,
                )


if __name__ == "__main__":
    main()
