import requests
import argparse
import os
import pymongo

from datetime import datetime

from transformers import AutoTokenizer, AutoModelForTokenClassification

from transformers import pipeline 

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

def load_ner_model(model_name):
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForTokenClassification.from_pretrained(model_name)
    return model, tokenizer

def connect_db():
    host = os.environ["DB_HOST"]
    port = int(os.environ["DB_MONGO_PORT"])
    database = os.environ["DB_MONGO_DATABASE"]
    user = os.environ["DB_MONGO_USER"]
    passw = os.environ["DB_MONGO_PASS"]
    client = pymongo.MongoClient(host, port, username=user, password=passw)
    logger.info("server_info():", client.server_info())
    return client[database]


def parsing_new_fact(db, collection):
    for record in db.collection.find({'parsed':{'$exists': False}}):
        yield record['_id'], record['text']


def ner_extraction(nlp, text):
    pers_keys = list()
    loc_keys = list()
    org_keys = list()
    oth_keys = list()

    ner_results = nlp(text)
    for entity in ner_results:
        if entity['entity_group'] == 'S_PERS':
            pers_keys.append(entity['word'])
        elif entity['entity_group'] == 'S_LOC':
            loc_keys.append(entity['word'])
        elif entity['entity_group'] == 'S_ORG':
            org_keys.append(entity['word'])
        elif entity['entity_group'] == 'S_OTH':
            oth_keys.append(entity['word'])
        else:
            pass

    return pers_keys + loc_keys + org_keys+  oth_keys


def create_unique_words(parsed_news):
    word_dict = dict()
    for i in parsed_news:
        for word in parsed_news[i]:
            word[word]
            word_dict.setdefault(word, []).append(i)
    return word_dict

def update_keywords_db(word_dict, db, collection):
    """
    """
    now = datetime.utcnow()
    for word in word_dict:
        db.collection.update_one({"word": word}, 
            {"$push": {'news_ids': { "$each": word_dict['news_ids'] } },
            'time': now }, 
            upsert=True)
    return True

def update_news():
    pass

def main():

    from dotenv import load_dotenv

    load_dotenv()

    # Load NER model
    logger.info('Load NER model')
    # model_name = "PlanTL-GOB-ES/roberta-base-bne-capitel-pos"
    model_name = "PlanTL-GOB-ES/roberta-base-bne-capitel-ner-plus"
    logger.info('Model loaded')
    # TODO the aggregation_strategy raises a warning because it is not 
    # implemented, while the doc says it is
    # https://huggingface.co/PlanTL-GOB-ES/roberta-base-bne-capitel-ner-plus/blob/main/README.md
    nlp = pipeline("ner", model=model_name, aggregation_strategy='first')
    logger.info("Connecting to the db")
    db = connect_db()
    col_maldita = 'maldita'
    col_keywords = 'keywords_twitter'

    dict_parsed_news = dict()
    for news_id, text in parsing_new_fact(db, col_maldita):
        dict_parsed_news[news_id] = ner_extraction(nlp, text)
    dict_to_insert = create_unique_words(dict_parsed_news)
    update_keywords_db(dict_to_insert, db, col_keywords) 



if __name__ == '__main__':
    main()
