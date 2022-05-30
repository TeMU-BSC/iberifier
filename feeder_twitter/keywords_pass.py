import os
import pymongo
from datetime import datetime
from collections import OrderedDict
import itertools

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


def insert_bigrams(db, collection, fact_id, bigrams):
    db[collection].update_one(
            {"_id": fact_id},
            {"$set": {"bigrams": bigrams}},
            upsert=False
        )
    return True


def check_cooccurrency(keywords, db, col_dict):
    return bool(db[col_dict].find_one({'words': {"$all": list(keywords)}}, {"_id": 0}))


def delete_from_cooccurrency(keywords_list, db, col_dict):
    try:
        for pairs in list(keywords_list):  # Need to create a copy of it to delete while looping
            if check_cooccurrency(pairs, db, col_dict):
                #print(keywords_list)
                #print(pairs)
                keywords_list.remove(pairs)
        return keywords_list
    except TypeError:  # Empty list
        raise("Issue with removing words from cooccurrency, probably empty list of keywords")


def create_bigrams(record, db, col_dict):

    def pairwise(iterable):
        a, b = itertools.tee(iterable)
        next(b, None)
        return zip(a, b)

    ner_words = list()
    pos_words = list()
    keywords_list = list()
    try:
        ner_ent = OrderedDict(record['NER'])
    except (KeyError, TypeError):
        ner_ent = None
    try:
        pos_ent = OrderedDict(record['POS'])
    except (KeyError, TypeError):
        pos_ent = None

    if ner_ent:
        for key in ner_ent:
            ner_words = ner_words + ner_ent[key]
        ner_words = list(set(ner_words))  # Sometimes same entity appears several times
        #print('NER WORDS: {}'.format(ner_words))
        # In case the list is at least two words
        if len(ner_words) >= 2:
            keywords_list = sorted(list(pairwise(ner_words)))
            keywords_list = delete_from_cooccurrency(keywords_list, db, col_dict)
            #keywords_list = list(itertools.permutations(ner_words, 2))
            # Again, checking if the resulting list without the cooccurrencies is still >=2
            if len(keywords_list) >=2:
                return keywords_list

    if pos_ent:
        for key in pos_ent:
            if key in ['NOUN', 'ADJ']:
                pos_words = pos_words + pos_ent[key] 
        # print("POS WORDS: {}".format(pos_words))
        full_list = sorted(ner_words + pos_words) # Sometimes same entity appears several times

        keywords_list = sorted(list(pairwise(full_list)))
        keywords_list = delete_from_cooccurrency(keywords_list, db, col_dict)
        return keywords_list


def getting_keywords(db, collection, col_dict):
    for record in db[collection].find({"LANG": {"$exists": True}}):
        fact_id = record['_id']
        keywords_list = create_bigrams(record, db, col_dict)

        yield fact_id, keywords_list


def main():


    ## DB Connection
    logger.info("Connecting to the db")
    db = connect_db(**mongodb_credentials)
    logger.info("Connected to: {}".format(db))
    col_maldita = "maldita"
    col_coocurence = 'cooccurrence'

    ## Running
    n  = 0
    for fact_id, keywords in getting_keywords(db, col_maldita, col_coocurence):
        insert_bigrams(db, col_maldita, fact_id, keywords)
        n+=1
    logger.info('Bigram creation for: {} records'.format(n))
    
if __name__ == "__main__":
    main()
