
import logging
import time
import os
import sys
import tqdm
import random
from datetime import datetime, timedelta
import logging.config
from itertools import combinations, chain


import yaml

from api_twitter import search_twitter

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from mongo_utils import mongo_utils

logger = logging.getLogger(__name__)

# Load config and credentials

config_path = os.path.join(os.path.dirname(
    __file__), "../config", "config.yaml")
config_all = yaml.safe_load(open(config_path))


logging_config_path = os.path.join(
    os.path.dirname(
        __file__), "../config", config_all["logging"]["logging_filename"]
)
with open(logging_config_path, "r") as f:
    yaml_config = yaml.safe_load(f.read())
    logging.config.dictConfig(yaml_config)

logger = logging.getLogger(config_all["logging"]["level"])

twitter_cred_path = os.path.join(
    os.path.dirname(__file__),
    "../config",
    config_all["api_twitter_params"]["cred_filename"],
)
twitter_credentials = yaml.safe_load(open(twitter_cred_path))[
    "search_tweets_api"]


def insert_tweets_mongo(tweet, fact_id, collection):
    collection.update_one(
        {"tweet_id": tweet["id"]},
        {
            "$set": {
                "tweet": tweet,
                "text": tweet["text"],
                "date": datetime.strptime(
                    tweet["created_at"].split(".")[0], "%Y-%m-%dT%H:%M:%S"
                ),
            },
            "$push": {"fact_id": fact_id},
        },
        upsert=True,
    )


def get_lists_ids(
    db,
    col_keywords,
    keywords_key,
    search_twitter_key,
    max_claims_per_day,
    days_before,
    days_after,
):
    limit_day = datetime.today() - timedelta(days=days_after + 1)
    aggregate_query = [
        {
            "$match": {
                "$and": [
                    {search_twitter_key: {"$exists": False}},
                    {keywords_key: {"$exists": True}},
                    {"date": {"$lt": limit_day}},
                    {"calification": "Falso"},
                ]
            },
        },
        {"$project": {"_id": 1}},
    ]
    results = [i["_id"] for i in db[col_keywords].aggregate(aggregate_query)]

    if max_claims_per_day:
        return random.sample(results, max_claims_per_day)
    return results


def get_documents(
    db,
    col_keywords,
    keywords_key,
    search_twitter_key,
    max_claims_per_day,
    days_before,
    days_after,
):
    list_ids = get_lists_ids(
        db,
        col_keywords,
        keywords_key=keywords_key,
        search_twitter_key=search_twitter_key,
        max_claims_per_day=max_claims_per_day,
        days_before=days_before,
        days_after=days_after,
    )

    tqdm_length = len(list_ids)
    cursor = db[col_keywords].find({"_id": {"$in": list_ids}}, batch_size=1)

    for record in tqdm.tqdm(cursor, total=tqdm_length):
        yield record
    cursor.close()


def split_call_per_day(date_fact_check, days_before, days_after):

    # dtformat = "%Y-%m-%dT%H:%M:%SZ"  # the date format string required by twitter
    dtformat = "%Y-%m-%dT%H:%M"  # the date format string required by twitter
    # if isinstance(date_fact_check, str):
    #     date_fact_check = datetime.strptime(date_fact_check, dtformat)
    # Set the time at midnight
    date_fact_check = date_fact_check.replace(
        hour=0, minute=0, second=0, microsecond=0)

    list_days = sorted(chain(range(1, days_after + 1),
                       range(0, -days_before - 1, -1)))

    for delta_days in list_days:
        # start_time is inclusive to the second (start to collect data from the lower limit)
        start_time = date_fact_check + timedelta(delta_days)
        # end_time is exclusive to the second (does not collect the data from the top limit)
        end_time = start_time + timedelta(1)
        start_time = start_time.strftime(dtformat)
        end_time = end_time.strftime(dtformat)
        yield start_time, end_time


def main():
    # Iterate through collection
    mydb = mongo_utils.get_mongo_db()
    col_keywords = config_all["mongodb_params"]["keywords"]["name"]
    col_tweets = config_all["mongodb_params"]["tweets"]["name"]

    strategy = config_all["keywords_params"]["strategy"]

    max_claims_per_day = config_all["api_twitter_params"]["max_claims_per_day"]
    search_twitter_key = config_all["api_twitter_params"]["search_twitter_key"]
    twitter_search_params = config_all["api_twitter_params"]["search_params"]
    twitter_rule_params = config_all["api_twitter_params"]["rule_params"]
    twitter_additional_query = twitter_search_params["additional_query"]
    days_before = twitter_search_params["days_before"]
    days_after = twitter_search_params["days_after"]

    # sources_to_update = []

    # get only the documents who were not searched for
    logger.info("Parsing the different claims")
    total_documents_done = 0 
    total_tweets_retrieved = 0
    earlier_day_retrieved = set()
    later_day_retrieved = set()
    n = 0
    for doc in get_documents(
        mydb,
        col_keywords,
        keywords_key=strategy,
        search_twitter_key=search_twitter_key,
        max_claims_per_day=max_claims_per_day,
        days_before=days_before,
        days_after=days_after,
    ):
        fact_id = doc["fact_id"]
        keyword_search = doc[strategy]
        size_keywords = 3

        query = ""
        if len(keyword_search) >= size_keywords:
            comb = combinations(keyword_search, 3)
        else:
            comb = [keyword_search]
        for i, c in enumerate(comb):
            if i == 0:
                query += "({})".format(" ".join(c))
            else:
                newquery = "({})".format(" ".join(c))
                if len(query) < 1024 - (len(" ".join(newquery))):
                    query += " OR " + newquery
                else:
                    break

        # Need to get the different day separately to ensure we do not hit the limit before getting the last day
        for start_time, end_time in split_call_per_day(doc['date'], days_before, days_after):
            earlier_day_retrieved.add(start_time)
            later_day_retrieved.add(end_time)
            twitter_rule_params["start_time"] = start_time
            twitter_rule_params["end_time"] = end_time
            tweets = search_twitter(
                twitter_credentials,
                query=query,
                search_params=twitter_search_params,
                rule_params=twitter_rule_params,
            )

            for tweet in tweets:
                insert_tweets_mongo(tweet, fact_id, mydb[col_tweets])
                total_tweets_retrieved +=1

            mydb[col_keywords].update_one(
                {"fact_id": fact_id}, {"$set": {search_twitter_key: datetime.now()}}
            )
            time.sleep(1)
        total_documents_done +=1
        if n == 5:
            break
    logger.info(f"Parsed {total_documents_done}")
    logger.info(f"Retrieved {total_tweets_retrieved}")
    logger.info(f"Covered the period from {min(earlier_day_retrieved)} to {max(later_day_retrieved)}")


if __name__ == "__main__":
    main()
