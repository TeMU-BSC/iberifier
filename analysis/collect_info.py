import logging
import os
import json
import sys
import logging.config

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


def _clean_result(result):
    to_return = result['_id']
    to_return['count'] = result['count']
    return to_return


def _return_aggregation(db, collection, query):

    return [_clean_result(i) for i in db[collection].aggregate(query)]


def count_per_day_fact_check(db, collection, field):

    query = [
        {
            "$group": {
                "_id": {
                    "date": {"$dateToString": {
                        "date": "$date",
                        "format": "%Y-%m-%d"}
                    },
                    "fact_checker": f"${field}",
                },
                'count': {'$sum': 1}
            }
        }
    ]
    return _return_aggregation(db, collection, query)


def count_per_day_tweets(db, collection):

    query = [
        {
            "$unwind": "$fact_id"},
        {
            "$group": {
                "_id": {
                    "date": {"$dateToString": {
                        "date": "$date",
                        "format": "%Y-%m-%d"}
                    },
                    "fact_id": {'$toString': "$fact_id"},
                },
                'count': {'$sum': 1}
            }
        }
    ]
    return _return_aggregation(db, collection, query)


def count_per_day_mynews(db, collection):

    query = [
        {
            "$group": {
                "_id": {
                    "date": {"$dateToString": {
                        "date": "$date",
                        "format": "%Y-%m-%d"}
                    },
                    "fact_id": {'$toString': "$fact_id"},
                    "newspaper": "$Newspaper"
                },
                'count': {'$sum': 1}
            }
        }
    ]
    return _return_aggregation(db, collection, query)


def main():
    # Iterate through collection
    mydb = mongo_utils.get_mongo_db()
    col_tweets = config_all['mongodb_params']['tweets']['name']
    col_mynews = config_all['mongodb_params']['mynews']['name']
    col_maldita = config_all['mongodb_params']['maldita']['name']
    field_maldita = config_all['api_maldita_params']['fields']['reviewer']
    field_google = config_all['api_google_params']['fields']['reviewer']
    col_google = config_all['mongodb_params']['google']['name']
    file_tweets = config_all['analysis']['count_day_tweets_file']
    file_google = config_all['analysis']['count_day_google_file']
    file_mynews = config_all['analysis']['count_day_mynews_file']
    file_maldita = config_all['analysis']['count_day_maldita_file']

    # result_per_day_google = count_per_day_fact_check(mydb, col_google, field_google)
    # result_per_day_maldita = count_per_day_fact_check(mydb, col_maldita, field_maldita)
    record_results(count_per_day_mynews(mydb, col_mynews), file_mynews)
    record_results(count_per_day_tweets(mydb, col_tweets), file_tweets)
    record_results(count_per_day_fact_check(mydb, col_google, field_google), file_google)
    record_results(count_per_day_fact_check(mydb, col_maldita, field_maldita), file_maldita)


if __name__ == "__main__":
    main()
