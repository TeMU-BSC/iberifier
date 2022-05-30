import re
from bs4 import BeautifulSoup
import string
import os
import pymongo
from datetime import datetime
from language_detector import detect_language

from transformers import AutoTokenizer, AutoModelForTokenClassification
from transformers import pipeline

# Credential loading
import importlib.util
spec = importlib.util.spec_from_file_location("credentials", os.getcwd()+"/credentials.py")
credentials = importlib.util.module_from_spec(spec)
spec.loader.exec_module(credentials)
mongodb_credentials = credentials.mongodb_credentials()

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


def connect_db(**kwargs):
    host = kwargs["DB_HOST"]
    port = int(kwargs["DB_MONGO_PORT"])
    database = kwargs["DB_MONGO_DATABASE"]
    try:
        user = kwargs["DB_MONGO_USER"]
    except KeyError:
        user = None
    try:
        passw = kwargs["DB_MONGO_PASS"]
    except KeyError:
        passw = None
    client = pymongo.MongoClient(host, port, username=user, password=passw)
    logger.info("server_info():", client.server_info())
    return client[database]


def parsing_new_fact(db, collection):
    for record in db[collection].find({"LANG": {"$exists": False}}):
        fact_id = record['_id']
        try:
            clean_content = BeautifulSoup(record['content'], "lxml").text
            text = record['text'] + ' ' + clean_content
        except TypeError:  # Maybe empty
            text = record['text']

        yield fact_id, text

def text_from_facts(db, collection):
    return parsing_new_fact(db, collection)

def extract_url(txt, compiled_url_regex):
    urls = compiled_url_regex.findall(txt)
    return urls

def clean_word(word):
    return word.strip().lower().translate(str.maketrans("", "", string.punctuation))


def detect_lang(txt):
    lang_dect = detect_language(txt)
    return lang_dect['pref_lang']


def entity_extraction(nlp, text):
    return_entity = dict()
    for ent in nlp(text):
        return_entity.setdefault(ent['entity_group'], set()).add(ent['word'].strip())
    for result in return_entity:
        return_entity[result] = list(return_entity[result])
    return return_entity


def create_unique_words(parsed_news):
    word_dict = dict()
    for i in parsed_news:
        for word in parsed_news[i]:
            word_dict.setdefault(word, []).append(i)
    return word_dict


def select_model(lang, model_es, model_pt, model_cat):
    if lang == 'es':
        return model_es
    elif lang == 'pt':
        return model_pt
    elif lang == 'ca':
        return model_cat
    else:
        pass


def update_fact(db, collection, fact_id,result_ner, result_pos, lang, urls):
    db[collection].update_one(
        {"_id": fact_id},
        {"$set": {'NER': result_ner, 
                  'POS': result_pos, 
                  "LANG": lang,
                  'URLS': urls}}
        )


def main():

    ## DB Connection
    logger.info("Connecting to the db")
    print(mongodb_credentials)
    db = connect_db(**mongodb_credentials)
    logger.info("Connected to: {}".format(db))
    col_maldita = "maldita"

    # Regex for URL extraction
    url_re = re.compile("http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+")

    # Load models

    ## ES MODEL FROM TEMU
    # TODO the aggregation_strategy raises a warning because it is not
    # implemented, while the doc says it is
    # https://huggingface.co/PlanTL-GOB-ES/roberta-base-bne-capitel-ner-plus/blob/main/README.md
    model_location_ner_es = "./models/roberta-base-bne-capitel-ner-plus/"
    nlp_ner_es = pipeline("ner", model=model_location_ner_es, tokenizer=model_location_ner_es, aggregation_strategy="simple") 
    logger.info('Load ES NER model: {}'.format(model_location_ner_es))
    #nlp_ner_es= pipeline("ner", model=model_name_ner_es, aggregation_strategy="first")

    model_name_pos_es = "PlanTL-GOB-ES/roberta-base-bne-capitel-pos"
    logger.info('Load ES POS model: {}'.format(model_name_pos_es))
    nlp_pos_es= pipeline("ner", model=model_name_pos_es, aggregation_strategy="simple")


    ## CAT MODEL FROM TEMU
    model_name_ner_cat = "projecte-aina/roberta-base-ca-cased-ner"
    logger.info('Load CAT NER model: {}'.format(model_name_ner_cat))
    nlp_ner_cat = pipeline('ner', model=model_name_ner_cat, aggregation_strategy='simple')

    model_name_pos_cat = "projecte-aina/roberta-base-ca-cased-pos"
    logger.info('Load CAT POS model: {}'.format(model_name_pos_cat))
    nlp_pos_cat = pipeline('ner', model=model_name_pos_cat, aggregation_strategy='simple')


    ## PT Model from: 
    model_name_ner_pt = "monilouise/ner_news_portuguese"
    logger.info('Load PT NER model: {}'.format(model_name_ner_pt))
    nlp_ner_pt= pipeline("ner", model=model_name_ner_pt, aggregation_strategy="simple")

    model_name_pos_pt = "PT_MODEL"
    logger.info('Load PT POS model: {}'.format(model_name_pos_pt))
    nlp_pos_pt= None 
    logger.info("Model loaded")



    ## Running
    for fact_id, text in text_from_facts(db, col_maldita):
        lang = detect_lang(text)
        if lang in ['es', 'ca', 'pt']:
            ner_model = select_model(lang, nlp_ner_es, nlp_ner_pt, nlp_ner_cat)
            pos_model = select_model(lang, nlp_pos_es, nlp_pos_pt, nlp_pos_cat)
            result_ner = None
            result_pos = None
            urls_extracted = extract_url(text, url_re)
            print(lang)
            print(text)
            result_ner = entity_extraction(ner_model, text)
            print('NER: {}'.format(result_ner))
            if lang == 'es' or lang == 'ca':
                result_pos = entity_extraction(pos_model, text)
                print('POS: {}'.format(result_pos))
            update_fact(db, col_maldita, fact_id, result_ner, result_pos, lang,  urls_extracted)

if __name__ == "__main__":
    main()
