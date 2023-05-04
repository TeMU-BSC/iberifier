import sys
import os
import tqdm

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from mongo_utils import mongo_utils
from bson.objectid import ObjectId

from datetime import datetime, timedelta
from sentence_transformers import SentenceTransformer, util
from transformers import pipeline, AutoTokenizer

# Logging options
# import logging
#
# logger_level = "DEBUG"
#
# logger = logging.getLogger(__name__)
# logger_set_level = getattr(logging, logger_level)
# logger.setLevel(logger_set_level)
# formatter = logging.Formatter("%(asctime)s :: %(levelname)s :: %(name)s :: %(message)s")


def get_source_keys(source):
    """Defines the right fields for each source"""
    source_keys = {}
    # if source == "telegram":
    #     source_keys["date"] = "date"
    #     source_keys["text"] = "message"
    if source == "tweets" or source == "tweets_new_call_strat":
        source_keys["date"] = "date"
        source_keys["text"] = "text"
    # elif source == "lusa":
    #     source_keys["date"] = "date"
    #     source_keys["text"] = "headline"
    elif source == "mynews":
        source_keys["date"] = "date"
        source_keys["text"] = "Title"
    return source_keys

def get_claim_ids(db, source, date_limit):
    collection = db[source]
    results = [i['_id'] for i in collection.find({"date": {"$gt": date_limit}, 'sts_already_done': {"$exists": False}, "calification": "Falso"})]
    return results

def get_claims(db, date_limit):
    list_ids = get_claim_ids(db, 'keywords', date_limit=date_limit)
    tqdm_length = len(list_ids)
    cursor = db['keywords'].find({'_id': {"$in": list_ids}}, batch_size=1)
    for record in tqdm.tqdm(cursor, total=tqdm_length):
        yield record
    cursor.close()

def get_list_ids(db, source, claim_id):
    collection = db[source]
    results = [i['_id'] for i in collection.find({'fact_id': claim_id})]
    return results

def get_messages(db, claim, source):
    print(claim['fact_id'])
    source_keys = get_source_keys(source)
    list_ids = get_list_ids(db, source, claim['fact_id'])
    tqdm_length = len(list_ids)
    cursor = db[source].find({'_id': {"$in": list_ids}}, batch_size=1)
    for record in tqdm.tqdm(cursor, total=tqdm_length):
        yield record, source_keys
    cursor.close()

def prepare(sentence_pairs, tokenizer):
    sentence_pairs_prep = []
    for s1, s2 in sentence_pairs:
        sentence_pairs_prep.append(f"{tokenizer.cls_token} {s1}{tokenizer.sep_token}{tokenizer.sep_token} {s2}{tokenizer.sep_token}")
    return sentence_pairs_prep


def main():
    # TODO: all these should come from config
    method = 'SentenceTransformers'
    chosen_model = 'distiluse_multi'
    threshold = 0.29
    source = 'mynews'
    date_limit = datetime(2023, 3, 15)
    labels = ['on-topic', 'off-topic']
    label_name = 'topic_relation'

    # connect to the mongo db
    #logger.info("Connecting to the db")
    db_iberifier = mongo_utils.get_mongo_db()

    # look for all the claims that have not been classified yet, add date limit for the search
    claims = get_claims(db_iberifier, date_limit)

    # choose a model
    if chosen_model == 'distiluse_multi':
        model = SentenceTransformer('sentence-transformers/distiluse-base-multilingual-cased')
    elif chosen_model == 'supervised_sts':
        path_sts = '../models/roberta-base-bne-sts'
        tokenizer_sts = AutoTokenizer.from_pretrained(path_sts)
        model = pipeline('text-classification', model=path_sts, tokenizer=tokenizer_sts, truncation=True)
    else:
        print('There is no such model.')
        exit()

    for claim_record in claims:
        for doc,source_keys in get_messages(db_iberifier, claim_record, source):
            if method == 'SentenceTransformers':
                embeddings = model.encode([claim_record['claim'], doc[source_keys["text"]]], convert_to_tensor=True)
                sim = util.cos_sim(embeddings[0], embeddings[1])
            elif method == 'supervised':
                c_predictions = model(prepare([(claim_record['claim'], doc[source_keys["text"]])], tokenizer_sts), add_special_tokens=False)
                sim = c_predictions[0]['score']
            else:
                print('There is no such method.')
                exit()

            if sim > threshold:
                db_iberifier[source].update_one({"_id": doc['_id']},
                                                    {"$set": {label_name: labels[0]}})
            else:
                db_iberifier[source].update_one({"_id": doc['_id']},
                                                {"$set": {label_name: labels[1]}})

        # update the claim witht a tag so it does not rerun
        db_iberifier['keywords'].update_one({"_id": claim_record['_id']}, {"$set": {'sts_already_done': datetime.now()}})





if __name__ == "__main__":
    main()
