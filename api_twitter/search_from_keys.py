import logging
import os
import sys
import tqdm
import random
from datetime import datetime, timedelta
import logging.config
from itertools import combinations
import pymongo

import yaml

from api_twitter import search_twitter
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from mongo_utils import mongo_utils

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

logger = logging.getLogger(config_all['logging']['level'])

twitter_cred_path = os.path.join(
    os.path.dirname(__file__),
    "../config",
    config_all["api_twitter_params"]["cred_filename"],
)
twitter_credentials = yaml.safe_load(open(twitter_cred_path))[
    "search_tweets_api"]


def insert_tweets_mongo(tweet, fact_id, collection):

    collection.update_one({"tweet_id": tweet["id"]},
                          {
        "$set": {'tweet': tweet,
                 'text': tweet['text'],
                 "date": datetime.strptime(tweet["created_at"].split('.')[0], '%Y-%m-%dT%H:%M:%S')
                 },
                              "$push": {'fact_id': fact_id}
    },
        upsert=True)


def get_lists_ids(db, col_keywords, keywords_key, search_twitter_key, max_claims_per_day, days_before, days_after):
    limit_day = datetime.today() - timedelta(days=days_after+1)
    aggregate_query = [
        {
            "$match": {
                "$and": [{
                    search_twitter_key: {'$exists': False}},
                    {'date': {'$lt': limit_day}}
                ]
            },

        },
        {
            "$project": {
                "_id": 1
            }
        }
    ]
    results = [i['_id'] for i in db[col_keywords].aggregate(aggregate_query)]

    if max_claims_per_day:
        return random.sample(results, max_claims_per_day)
    return results


def get_documents(db, col_keywords, keywords_key, search_twitter_key, max_claims_per_day, days_before, days_after):

    list_ids = get_lists_ids(db, col_keywords, keywords_key=keywords_key, search_twitter_key=search_twitter_key,
                             max_claims_per_day=max_claims_per_day, days_before=days_before, days_after=days_after)

    tqdm_length = len(list_ids)
    cursor = db[col_keywords].find({'_id': {"$in": list_ids}}, batch_size=1)

    for record in tqdm.tqdm(cursor, total=tqdm_length):
        yield record
    cursor.close()


def main():
    # Iterate through collection
    mydb = mongo_utils.get_mongo_db()
    col_keywords = config_all['mongodb_params']['keywords']['name']
    col_tweets = config_all['mongodb_params']['tweets']['name']

    strategy = config_all['keywords_params']['strategy']

    max_claims_per_day = config_all['api_twitter_params']['max_claims_per_day']
    search_twitter_key = config_all['api_twitter_params']['search_twitter_key']
    twitter_search_params = config_all['api_twitter_params']['search_params']
    twitter_rule_params = config_all['api_twitter_params']['rule_params']
    twitter_additional_query = twitter_search_params['additional_query']
    days_before = twitter_search_params['days_before']
    days_after = twitter_search_params['days_after']

    # sources_to_update = []

    # get only the documents who were not searched for
    logger.info("Parsing the different claims")
    for doc in get_documents(mydb, col_keywords,
                             keywords_key=strategy,
                             search_twitter_key=search_twitter_key,
                             max_claims_per_day=max_claims_per_day,
                             days_before=days_before, days_after=days_after):
        fact_id = doc["fact_id"]
        post_date_str = doc['date']
        # post_date = datetime.strptime(post_date_str, "%Y-%m-%dT%H:%M:%S%z")
        twitter_search_params['date'] = post_date_str
        keyword_search = doc[strategy]


        query = ''
        comb = combinations(keyword_search, 3)
        for i,c in enumerate(comb):
            if i == 0:
                query += "({})".format(' '.join(c))
            else:
                newquery = "({})".format(' '.join(c))
                if len(query) < 1024 - (len(" ".join(newquery))):
                    query += " OR " + newquery
                else:
                    break

        tweets = search_twitter(
                twitter_credentials, query=query, search_params=twitter_search_params, rule_params=twitter_rule_params)

        for tweet in tweets:
            insert_tweets_mongo(tweet, fact_id,  mydb[col_tweets])

        mydb[col_keywords].update_one(
            {"fact_id": fact_id}, {
                "$set": {search_twitter_key: datetime.now()}})


if __name__ == "__main__":
    main()
