
import pymongo
from language_detector import detect_language
from datetime import datetime
from collections import OrderedDict
import itertools

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

def getting_keywords(db, collection):
    for record in db[collection].find({"LANG": {"$exists": True}}):
        ner_words = list()
        pos_words = list()
        keywords_list = list()
        fact_id = record['_id']
        try:
            ner_ent = OrderedDict(record['NER'])
        except KeyError:
            ner_ent = None
        try:
            pos_ent = OrderedDict(record['POS'])
            del pos_ent['VERB']  # Not working well in twitter 
        except KeyError:
            pos_ent = None

        if ner_ent:
            for key in ner_ent:
                ner_words = ner_words + ner_ent[key]

            # In case the list is at least two words
            if len(ner_words) >= 2:
                keywords_list = list(itertools.permutations(ner_words, 2))
                yield fact_id, keywords_list

        if pos_ent:
            for key in pos_ent:
                pos_words = pos_words + pos_ent[key]

            full_list = ner_words + pos_words
            keywords_list = list(itertools.permutations(full_list, 2))
            # ner_ent_keys = list(ner_ent)  # Get the list of keys 
            # try:
            #     for i, key in enumerate(ner_ent_keys):
            #         for word in ner_ent[key]:
            #             for word2 in ner_ent[ner_ent_keys[i+1]]:

            #                 word_combination = sorted(tuple[word, word2])
            #                 # word_combination = '{} AND {}'.format(word, word2)
            #                 keywords_list.append(word_combination)
            # except IndexError:
            #     pass
                
                

        yield fact_id, keywords_list


def main():

    ## DB Connection
    logger.info("Connecting to the db")
    db = connect_db(mongodb_credentials)
    logger.info("Connected to: {}".format(db))
    col_maldita = "maldita"

    ## Running
    for fact_id, keywords in getting_keywords(db, col_maldita):
        print(fact_id, keywords)
    
if __name__ == "__main__":
    main()
