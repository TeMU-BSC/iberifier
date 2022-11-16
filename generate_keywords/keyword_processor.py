import yaml
import argparse
import itertools
import logging
import logging.config
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
from mongo_utils import mongo_utils


config_path = os.path.join(os.path.dirname(
    __file__), '../config', 'config.yaml')
config_all = yaml.safe_load(open(config_path))

logging_config_path = os.path.join(os.path.dirname(
    __file__), '../config', config_all['logging']['logging_filename'])
with open(logging_config_path,  "r") as f:
    yaml_config = yaml.safe_load(f.read())
    logging.config.dictConfig(yaml_config)

logger = logging.getLogger(config_all['logging']['level'])


# Setting up to rerun or not (True/False)
# RERUN = False


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
        default=None,
        type=int,
        help="Number of days to compute",
    )
    return parser


def remove_nonalpha(strings):
    new = []
    for s in strings:
        new.append(''.join(x for x in s if x.isalpha()))
    new = list(set([n for n in new if n != '']))
    return new


def create_keyword_list(ner_ent=None, pos_ent=None):
    ner_words = list()
    pos_words = list()

    if ner_ent:
        for key in ner_ent:
            ner_words = ner_words + ner_ent[key]
        # Sometimes same entity appears several times
        ner_words = list(set(ner_words))

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


def create_and_filter_pairs(db, keywords):
    filtered_pairs = []
    pairs = ((x, y) for x in keywords for y in keywords if y > x)
    for pair in pairs:
        # filter pairs that are too co-occurring
        check = [x.lower() for x in pair]
        # TODO: cooccurrence dictionaty has to be bigger and dynamic
        cursor = db["cooccurrence"].find_one({'words': check})
        # TODO: these still takes quite too much time, find if we have a better solution -> olivier will index
        if cursor:
            if cursor['counts'] > 15:  # TODO is it the threshold we mention last time?
                continue
        filtered_pairs.append(pair)
    return filtered_pairs


def main():

    parser = argparse.ArgumentParser()
    parser = get_arguments(parser)
    args = parser.parse_args()

    # DB Connection
    logger.info("Connecting to the db")
    db = mongo_utils.get_mongo_db()
    logger.info("Connected to: {}".format(db))
    #col_cooccurence = "cooccurrence"

    # Load models
    dict_models = config_all['keywords_params']['language_models']

    # Running
    for col_to_parse in ["maldita", "google"]:
        # TODO: detect the languages in the batch and load the models one time
        for fact_id, text, content, lang in text_from_facts(db, col_to_parse, args):
            if lang is None:
                lang = detect_lang(text)
            if lang in ["es", "ca", "pt"]:
                ner_model = select_model(
                    lang, nlp_ner_es, nlp_ner_pt)
                pos_model = select_model(
                    lang, nlp_pos_es, nlp_pos_pt)

                text, urls_extracted = extract_url(text)

                ner_entities = entity_extraction(ner_model, text)
                pos_entities = entity_extraction(pos_model, text)
                

                keywords = get_ner(ner_model, text)
                result_pos = get_pos(pos_model, text, "NOUN")
                keywords += result_pos
                keywords = remove_nonalpha(keywords)

                # if this does not give enough keywords, try other ways, these ways are ordered strategically

                if len(keywords) < 3:
                    if content != None:
                        content_ner = get_ner(ner_model, content)
                        content_ner = remove_nonalpha(content_ner)
                        keywords += content_ner
                if len(keywords) < 3:
                    content_pos = get_pos(pos_model, content, "NOUN")
                    content_pos = remove_nonalpha(content_pos)
                    keywords += content_pos

                if len(keywords) < 3:
                    adjectives = get_pos(pos_model, text, "ADJ")
                    adjectives = remove_nonalpha(adjectives)
                    keywords += adjectives
                if len(keywords) < 3:
                    verbs = get_pos(pos_model, text, "VERB")
                    verbs = remove_nonalpha(verbs)
                    keywords += verbs

                if len(keywords) > 6:
                    keywords = keywords[:6]
                keywords.sort()
                print(text)
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
