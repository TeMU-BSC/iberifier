import sys
import os
import tqdm
import yaml

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from mongo_utils import mongo_utils
from bson.objectid import ObjectId

from nltk.tokenize import word_tokenize
from datetime import datetime, timedelta

# Logging options
import logging

logger = logging.getLogger(__name__)

# Load config and credentials

config_path = os.path.join(os.path.dirname(
    __file__), '../config', 'config.yaml')
config_all = yaml.safe_load(open(config_path))


logging_config_path = os.path.join(os.path.dirname(
    __file__), '../config', config_all['logging']['logging_filename'])
with open(logging_config_path,  "r") as f:
    yaml_config = yaml.safe_load(f.read())
    logging.config.dictConfig(yaml_config)

def select_messages_timeframe(time, messages, timeframe, source):
    x = time - timedelta(days=timeframe)
    y = time + timedelta(days=timeframe)
    print(time, messages, timeframe, source, x, y)
    selection = list(messages.find({source["date"]: {"$gt": x, "$lt": y}})) # also filter by related to
    return selection

def get_list_ids(collection, claim_id):
    results = [i['_id'] for i in collection.find({'fact_id': claim_id})]
    return results

def get_messages(collection, claim):
    list_ids = get_list_ids(collection, claim)
    tqdm_length = len(list_ids)
    cursor = collection.find({'_id': {"$in": list_ids}}, batch_size=1)
    for record in tqdm.tqdm(cursor, total=tqdm_length):
        yield record
    cursor.close()

def select_claims(collection, keywords_key):
    aggregation_strategy = [
        {
            "$match": {
                "$and": [
                    {"search_mynews_key": {"$exists": True}},
                    {keywords_key: {"$exists": True}},
                    {"filtered_mynews_by_keywords": {"$exists": False}}
                ]
            },
        },
        {"$project": {"_id": 1}},
    ]
    #for i in collection.aggregate(aggregation_strategy):
    #    print(i)
    results = [i['_id'] for i in collection.aggregate(aggregation_strategy)]
    return results


def main():
    # connect to the mongo db
    logger.info("Connecting to the db")
    db_iberifier = mongo_utils.get_mongo_db()

    # look for one claim in the fact-check database
    keywords_collection = db_iberifier["keywords"]
    mynews_collection = db_iberifier["mynews"]
    keywords_key = config_all["keywords_params"]["strategy"]

    # filter by the claims that have mynews key but have not been filtered
    claims = select_claims(keywords_collection, keywords_key)

    # check if the title contains at least one keyword
    for claim in claims:
        count = 0
        entry = keywords_collection.find_one({"_id": claim})
        for doc in get_messages(mynews_collection, entry['fact_id']):
            found_key = False
            tokenized_title = word_tokenize(doc['Title'])
            for k in entry[keywords_key]:
                if k in tokenized_title:
                    count += 1
                    found_key = True
                    break
            if found_key:
                mynews_collection.update_one({"_id": doc['_id']},{"$set": {"keywords_in_title": True}})
            else:
                mynews_collection.update_one({"_id": doc['_id']}, {"$set": {"keywords_in_title": False}})
        keywords_collection.update_one({"_id": claim},{"$set": {"filtered_mynews_by_keywords": datetime.now()}})
        print(count)


if __name__ == "__main__":
    main()
