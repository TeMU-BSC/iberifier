import datetime
import json
import logging
import logging.config
import os
import sys

import pymongo
import yaml

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from mongo_utils import mongo_utils

logger = logging.getLogger(__name__)

# Load config and credentials

config_path = os.path.join(os.path.dirname(
    __file__), '../config', 'config.yaml')
config_all = yaml.safe_load(open(config_path))


def record_results(result, file_location):
    with open(file_location, 'w') as f:
        json.dump(result, f)

def clean_result(record):
    # Transform the ObjecID into  string
    try:
        record['fact_id'] = str(record['fact_id'])
    except KeyError:
        return
    try:
        record['_id'] = str(record['_id'])
    except KeyError:
        return
    try:
        record['tweet_id'] = record['tweet']['tweet_id']
    except KeyError:
        return
    try:
        record['tweet_text'] = record['tweet']['text']
    except KeyError:
        return
    try:
        record["tweet_date"] = datetime.datetime.strftime(record['tweet']['date'], "%Y-%m-%d")
    except KeyError:
        return
    try:
        record['date'] = datetime.datetime.strftime(record['date'], "%Y-%m-%d")
    except KeyError:
        return

    del record['tweet']

    for key in ['claim', 'review']:
        try:
            record[key]
        except KeyError:
            record[key] = None

    return record

def _return_aggregation(db, collection, query,):

    for i in db[collection].aggregate(query):
        yield i

def random_fact_ids(db: pymongo.database, 
                    collection: pymongo.collection, 
                    from_date: datetime.datetime, 
                    to_date: datetime.datetime, 
                    number_per_day: int=1,
                    field_claim: str=None,
                    field_review: str=None) -> dict:
    """
    Get nth random fact_id per day between two specified date
    The nth random fact_ids are only the nth first element of a list per date 
    Params:
        db Mongodb()
        collection Mongodb collection()
        number_per_day int()
        from_date datetime()
        to_date datetime()
    """
    query = [
        # Group the records per day and append a list with all the fact_id from the same date
        {"$match": {'date': {"$gte": from_date, "$lte": to_date}, 
                    'organizationCalification.calification.name': 'Falso',  #FIXME This line is for Maldita, not works with Google and will return empty
                    field_claim: {'$ne': None},
                    field_review: {'$ne': None},
                    'organization.name': {'$ne': 'Polígrafo'},
                    }
         }, 
        {"$group": {
            "_id": {
                "date": {"$dateToString": {
                    "date": "$date",
                    "format": "%Y-%m-%d"}
                         }
                },
            "fact_ids": { "$push": "$_id"}
            }
         },
        # Project the field and slice the list of fact_id to get nth elements
        {"$project": {
            '_id': 0,
            'date': "$_id.date",
            'fact_id': {
                "$slice": ["$fact_ids", number_per_day] }
            }
         },
        # Unwind on the random_fact_ids to get access to the fact_id
        {'$unwind': "$fact_id"},
    ]
    return _return_aggregation(db, collection, query)

def getting_random_tweets(db, col_tweets, col_keywords, fact_id, sample_size):
    query = [
            {'$match': {'fact_id': fact_id}},
            {'$lookup': {
                "from": col_tweets,
                "let": {'fact_id_from_key': '$fact_id'},
                'pipeline':[
                    {
                        "$match": {
                            "$expr": {
                                "$in": ["$$fact_id_from_key", "$fact_id"],
                                }
                            }
                        },

                        {'$sample': {'size': sample_size}}
                    ],

                'as': 'tweet'
                }
             },

            {'$unwind': '$tweet'},
            {'$project': {"date": 1, 'fact_id': 1, 'tweet.text': 1, 'tweet.tweet_id': 1, 'tweet.date': 1, 'claim': 1, 'review': 1},},
            ]
    return _return_aggregation(db, col_keywords, query)


def main():
    # Iterate through collection
    mydb = mongo_utils.get_mongo_db()
    col_tweets = config_all['mongodb_params']['tweets']['name']
    col_mynews = config_all['mongodb_params']['mynews']['name']
    col_maldita = config_all['mongodb_params']['maldita']['name']
    col_keywords = config_all['mongodb_params']['keywords']['name']
    field_maldita = config_all['api_maldita_params']['fields']['reviewer']
    field_claim_maldita = config_all['api_maldita_params']['fields']['claim']
    field_review_maldita = config_all['api_maldita_params']['fields']['review']
    field_google = config_all['api_google_params']['fields']['reviewer']
    col_google = config_all['mongodb_params']['google']['name']
    file_tweets = config_all['analysis']['count_day_tweets_file']
    file_google = config_all['analysis']['count_day_google_file']
    file_mynews = config_all['analysis']['count_day_mynews_file']
    file_maldita = config_all['analysis']['count_day_maldita_file']

    from_date = datetime.datetime(2022, 12, 26) 
    to_date = datetime.datetime(2023, 1, 26)
    sample_size_claim_per_day = 2
    sample_size_tweet_per_claim = 20
    file_sample_location = './data/sample_claim_tweets.jsonl'

    total_tweets = 0
    nbr_claims = 0
    first_record = True
    with open(file_sample_location, 'a', encoding='utf-8') as outfile:
        for fact_id in random_fact_ids(mydb, col_maldita, from_date, to_date,  sample_size_claim_per_day, field_claim_maldita, field_review_maldita):
            nbr_claims += 1
            for result in getting_random_tweets(mydb, col_tweets, col_keywords, fact_id['fact_id'], sample_size_tweet_per_claim):
                result = clean_result(result)
                if result:
                    if first_record is False:
                        outfile.write('\n')
                    total_tweets += 1
                    print(f"Number of claims: {nbr_claims} = Total tweets: {total_tweets}")
                    json_record = json.dumps(result, ensure_ascii=False)
                    outfile.write(json_record)
                    first_record = False
    print("Record into jsonl")


if __name__ == "__main__":
    main()
