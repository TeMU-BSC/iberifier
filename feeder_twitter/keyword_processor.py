from bs4 import BeautifulSoup
import string
import os
import pymongo
from language_detector import detect_language
from datetime import datetime

from transformers import AutoTokenizer, AutoModelForTokenClassification
from transformers import pipeline

# Credential loading
import importlib.util
spec = importlib.util.spec_from_file_location("credentials", os.getcwd()+"/credentials.py")
credentials = importlib.util.module_from_spec(spec)
spec.loader.exec_module(credentials)
mongodb_credentials = credentials.mongodb_credentials

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


def connect_db(*args, **kwargs):
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

def clean_word(word):
    return word.strip().lower().translate(str.maketrans("", "", string.punctuation))


def detect_lang(text):
    lang_dect = detect_language(text)
    return lang_dect['pref_lang']


def ner_extraction(nlp, text):
    return_ner = dict()

    ner_results = nlp(text)
    iter_ner = iter(ner_results)
    while True:
        try:
            entity = next(iter_ner)
        except StopIteration:
            break
        type_entity = entity["entity_group"]
        word = clean_word(entity["word"])
        if type_entity.startswith("S_"):
            return_ner.setdefault(type_entity[2:], []).append(word)

        elif type_entity.startswith("B_"):
            try:
                b_ent2 = next(iter_ner)
                type_entity2 = b_ent2["entity_group"]
                b_word2 = clean_word(b_ent2["word"])
                if type_entity2.startswith("E_"):
                    b_word = word + " " + b_word2
                    return_ner.setdefault(type_entity[2:], []).append(b_word)

                elif type_entity2.startswith("I_"):
                    try:
                        b_ent3 = next(iter_ner)
                        type_entity3 = b_ent3["entity_group"]
                        b_word3 = clean_word(b_ent3["word"])
                        if type_entity3.startswith("E_"):
                            b_word = word + " " + b_word3
                            return_ner.setdefault(type_entity[2:], []).append(b_word)
                        else:
                            return_ner.setdefault(type_entity[2:], []).append(word)
                            return_ner.setdefault(type_entity[2:], []).append(b_word3)
                    except StopIteration:
                        return_ner.setdefault(type_entity[2:], []).append(b_word)
                        break

                else:
                    return_ner.setdefault(type_entity[2:], []).append(word)
            except StopIteration:
                return_ner.setdefault(type_entity[2:], []).append(word)
                break

    ## Ensuring unique key  # TODO add to set instead of list
    for k in return_ner:
        return_ner[k] = list(set(return_ner[k]))
    return return_ner

def pos_extraction(nlp, text):
    return_pos = dict()
    pos_result = nlp(text)

    for word in pos_result:
        if word['entity_group'] == 'NOUN':
            return_pos.setdefault(word['entity_group'], []).append(clean_word(word['word']))
        elif word['entity_group'] == 'VERB':
            return_pos.setdefault(word['entity_group'], []).append(clean_word(word['word']))
        elif word['entity_group'] == 'ADJ':
            return_pos.setdefault(word['entity_group'], []).append(clean_word(word['word']))

    
    ## Ensuring unique key  # TODO add to set instead of list
    for k in return_pos:
        return_pos[k] = list(set(return_pos[k]))

    return return_pos


def create_unique_words(parsed_news):
    word_dict = dict()
    for i in parsed_news:
        for word in parsed_news[i]:
            # word[word]
            word_dict.setdefault(word, []).append(i)
    return word_dict


def update_keywords_db(word_dict, db, collection):
    """ """
    now = datetime.utcnow()
    for word in word_dict:
        db[collection].update_one(
            {"word": word},
            {"$push": {"news_ids": {"$each": word_dict[word]}}, "$set": {"time": now}},
            upsert=True,
        )
    return True


def select_model(lang, model_es, model_pt, model_cat):
    if lang == 'es':
        return model_es
    elif lang == 'pt':
        return model_pt
    elif lang == 'ca':
        return model_cat
    else:
        pass


def update_fact(db, collection, fact_id,result_ner, result_pos, lang):
    db[collection].update_one(
        {"_id": fact_id},
        {"$set": {'NER': result_ner, 'POS': result_pos, "LANG": lang}}
        )


def main():


    # Load models

    ## ES MODEL FROM TEMU
    # TODO the aggregation_strategy raises a warning because it is not
    # implemented, while the doc says it is
    # https://huggingface.co/PlanTL-GOB-ES/roberta-base-bne-capitel-ner-plus/blob/main/README.md
    model_name_ner_es = "PlanTL-GOB-ES/roberta-base-bne-capitel-ner-plus"
    logger.info('Load ES NER model: {}'.format(model_name_ner_es))
    nlp_ner_es= pipeline("ner", model=model_name_ner_es, aggregation_strategy="first")

    model_name_pos_es = "PlanTL-GOB-ES/roberta-base-bne-capitel-pos"
    logger.info('Load ES POS model: {}'.format(model_name_pos_es))
    nlp_pos_es= pipeline("ner", model=model_name_pos_es, aggregation_strategy="first")


    ## CAT MODEL FROM TEMU
    model_name_ner_cat = "projecte-aina/roberta-base-ca-cased-ner"
    logger.info('Load CAT NER model: {}'.format(model_name_ner_cat))
    nlp_ner_cat = pipeline('ner', model=model_name_ner_cat, aggregation_strategy='first')

    model_name_pos_cat = "projecte-aina/roberta-base-ca-cased-pos"
    logger.info('Load CAT NER model: {}'.format(model_name_pos_cat))
    nlp_pos_cat = pipeline('ner', model=model_name_pos_cat, aggregation_strategy='first')


    ## PT Model from: 
    model_name_ner_pt = "monilouise/ner_news_portuguese"
    logger.info('Load PT NER model: {}'.format(model_name_ner_pt))
    nlp_ner_pt= pipeline("ner", model=model_name_ner_pt, aggregation_strategy="first")

    model_name_pos_pt = "PT_MODEL"
    logger.info('Load PT POS model: {}'.format(model_name_pos_pt))
    nlp_pos_pt= None 
    logger.info("Model loaded")


    ## DB Connection
    logger.info("Connecting to the db")
    db = connect_db(mongodb_credentials)
    logger.info("Connected to: {}".format(db))
    col_maldita = "maldita"

    ## Running
    for fact_id, text in text_from_facts(db, col_maldita):
        lang = detect_lang(text)
        ner_model = select_model(lang, nlp_ner_es,nlp_ner_pt, nlp_ner_cat)
        pos_model = select_model(lang, nlp_pos_es, nlp_pos_pt, nlp_pos_cat)
        # TODO: Remove as soon as getting a pt model for ner and pos
        if lang == 'es' or lang == 'ca':
            result_ner = ner_extraction(ner_model, text)
            result_pos = pos_extraction(pos_model, text)
            update_fact(db, col_maldita, fact_id, result_ner, result_pos, lang)

if __name__ == "__main__":
    main()
