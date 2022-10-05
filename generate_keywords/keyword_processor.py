#from genericpath import commonprefix
import re
from bs4 import BeautifulSoup
import string

import itertools
from datetime import datetime, timedelta
#from collections import OrderedDict
from language_detector import detect_language
import argparse
import sys, os

#from transformers import AutoTokenizer, AutoModelForTokenClassification
from transformers import pipeline

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from mongo_utils import mongo_utils

## Setting up to rerun or not (True/False)
#RERUN = False

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
    lang,
    urls,
    keywords,
    keyword_pairs,
):
    db[collection].update_one(
        {"_id": fact_id},
        {
            "$set": {
                "LANG": lang,
                "URLS": urls,
                "keywords": keywords,
                "keyword_pairs": keyword_pairs,
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
        if len(ner_words) >= 2:
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


def extract_url(txt):
    url_re = re.compile("http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+")
    txt, urls = remove_compiled_regex(txt=txt, compiled_regex=url_re)
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

def get_arguments(parser):
    parser.add_argument(
        "--historical",
        action='store_true',
        help="use when there is a lot of data, and not just the daily run",
    )
    parser.add_argument(
        "--rerun",
        action='store_true',
        help="rerun the keywords generation",
    )
    parser.add_argument(
        "--time_window",
        action='store_true',
        help="compute keywords just for the last two days",
    )
    return parser

def detect_lang(txt):
    lang_dect = detect_language(txt)
    return lang_dect["pref_lang"]


def parsing_new_fact_maldita(db, collection, search):
    cursor = db[collection].find(search)
    for record in cursor:
        #print(record)
        fact_id = record["_id"]
        text = record["text"]
        try:
            content = BeautifulSoup(record["content"], "lxml").text
            #text = record["text"] + " " + clean_content
        except TypeError:  # Maybe empty
            content = None

        print(text)
        yield fact_id, text, content, None
    cursor.close()


def parsing_new_fact_google(db, collection, search):
    cursor = db[collection].find(search, batch_size=1)
    for record in cursor:
        fact_id = record["_id"]
        text = record["text"]
        content = record["claimReview"][0]["title"]
        lang = record["claimReview"][0]["languageCode"]
        yield fact_id, text, content, lang
    cursor.close()


def text_from_facts(db, collection, args):
    search = {}
    if not args.rerun:
        search["keyword_pairs"] = {"$exists": False}
    if args.time_window:
        today = datetime.today()
        days_ago = today - timedelta(days=1)
        search["date"] = {'$gt': days_ago, '$lt': today}
    if collection == "maldita":
        print('Searching in maldita for:',search)
        return parsing_new_fact_maldita(db, collection, search)
    elif collection == "google":
        print('Searching in google for:',search)
        return parsing_new_fact_google(db, collection, search)
    else:
        raise Exception("Not the right collection")

def load_nlp_model(task, lang, models):
    logger.info("Load {} {} model: {}".format(lang, task, models[(task,lang)]))
    nlp_model = pipeline(
        ("token-classification" if task=="pos" else task),
        model=models[(task,lang)],
        tokenizer=models[(task,lang)],
        aggregation_strategy="max",
    )
    return nlp_model

def remove_nonalpha(strings):
    new = []
    for s in strings:
        new.append(''.join(x for x in s if x.isalpha()))
    new = list(set([n for n in new if n !='']))
    return new

def get_pos(pos_model, text, type):
    pos = []
    try:
        for element in pos_model(text):
            if element['entity_group'] == type: #or element['entity_group'] == 'PROPN':
                pos.append(element['word'])
        return pos
    except:
        return []

def get_ner(ner_model, text):
    ner = []
    try:
        for entity in ner_model(text):
            ner.append(entity['word'])
        return ner
    except:
        return []

def create_and_filter_pairs(db, keywords):
    filtered_pairs = []
    pairs = ((x, y) for x in keywords for y in keywords if y > x)
    for pair in pairs:
        #print(pair)
        # filter pairs that are too co-occurring
        check = [x.lower() for x in pair]
        #print(check)
        cursor = db["cooccurrence"].find_one({'words':check}) # TODO: cooccurrence dicionaty has to be bigger and dynamic
        # TODO: these still takes quite too much time, find if we have a better solution -> olivier will index
        if cursor:
            #print(cursor['counts'])
            if cursor['counts'] > 15:
                continue
        filtered_pairs.append(pair)
        #print(filtered_pairs)
    return filtered_pairs

def main():

    parser = argparse.ArgumentParser()
    parser = get_arguments(parser)
    args = parser.parse_args()
    print(args)

    ## DB Connection
    logger.info("Connecting to the db")
    db = mongo_utils.get_mongo_db()
    logger.info("Connected to: {}".format(db))
    #col_cooccurence = "cooccurrence"

    # Load models
    dict_models = {("ner","es"):"PlanTL-GOB-ES/roberta-base-bne-capitel-ner-plus",
                   ("pos","es"):"PlanTL-GOB-ES/roberta-base-bne-capitel-pos",
                   ("ner", "ca"):"projecte-aina/roberta-base-ca-cased-ner",
                   ("pos", "ca"): "projecte-aina/roberta-base-ca-cased-pos",
                   ("ner", "pt"): "monilouise/ner_news_portuguese",
                   ("pos", "pt"): "wietsedv/xlm-roberta-base-ft-udpos28-pt"
                   }
    if args.historical: # loading all the models is not efficient in daily calls
        nlp_ner_es = load_nlp_model("ner", "es", dict_models)
        nlp_pos_es = load_nlp_model("pos", "es", dict_models)
        nlp_ner_cat = load_nlp_model("ner", "ca", dict_models)
        nlp_pos_cat = load_nlp_model("pos", "ca", dict_models)
        nlp_ner_pt = load_nlp_model("ner", "pt", dict_models)
        nlp_pos_pt = load_nlp_model("pos", "pt", dict_models)

    ## Running
    for col_to_parse in ["maldita", "google"]:
        for fact_id, text, content, lang in text_from_facts(db, col_to_parse, args): # TODO: detect the languages in the batch and load the models one time
            if lang is None:
                lang = detect_lang(text)
            if lang in ["es", "ca", "pt"]:
                if args.historical:
                    ner_model = select_model(lang, nlp_ner_es, nlp_ner_pt, nlp_ner_cat)
                    pos_model = select_model(lang, nlp_pos_es, nlp_pos_pt, nlp_pos_cat)
                else:
                    ner_model = load_nlp_model("ner", lang, dict_models)
                    pos_model = load_nlp_model("pos", lang, dict_models)

                text, urls_extracted = extract_url(text)
                #print(urls_extracted)

                keywords = get_ner(ner_model, text)
                result_pos = get_pos(pos_model, text, "NOUN")
                keywords += result_pos
                keywords = remove_nonalpha(keywords)

                # if this does not give enough keywords, try other ways, these ways are ordered strategically

                if len(keywords) < 4:
                    if content != None:
                        content_ner = get_ner(ner_model, content)
                        content_ner = remove_nonalpha(content_ner)
                        keywords += content_ner
                if len(keywords) < 4:
                    content_pos = get_pos(pos_model, content, "NOUN")
                    content_pos = remove_nonalpha(content_pos)
                    keywords += content_pos

                if len(keywords) < 4:
                    adjectives = get_pos(pos_model, text, "ADJ")
                    adjectives = remove_nonalpha(adjectives)
                    keywords += adjectives
                if len(keywords) < 4:
                    verbs = get_pos(pos_model, text, "VERB")
                    verbs = remove_nonalpha(verbs)
                    keywords += verbs

                keywords.sort()
                print('KEYWORDS:', keywords)

                if len(keywords) == 0:
                    print('empty example')
                    print(lang)
                else:
                    keyword_pairs = create_and_filter_pairs(db, keywords)
                    print('KEYWORD PAIRS:', keyword_pairs)

                    update_fact(
                        db,
                        col_to_parse,
                        fact_id,
                        lang,
                        urls_extracted,
                        keywords,
                        keyword_pairs,
                    )


if __name__ == "__main__":
    main()
