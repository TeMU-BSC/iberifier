import logging
import logging.config
import sys
from googleapiclient.discovery import build
import argparse
import time
import os
import yaml
from pymongo.errors import BulkWriteError
import datetime


sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from mongo_utils import mongo_utils

config_path = os.path.join(os.path.dirname(
    __file__), '../config', 'config.yaml')
config_all = yaml.safe_load(open(config_path))

google_cred_path = os.path.join(
    os.path.dirname(__file__),
    "../config",
    config_all["api_google_params"]["cred_filename"],
)
google_credentials = yaml.safe_load(open(google_cred_path))[
    "google_api_credentials"]

logging_config_path = os.path.join(os.path.dirname(
    __file__), '../config', config_all['logging']['logging_filename'])
with open(logging_config_path,  "r") as f:
    yaml_config = yaml.safe_load(f.read())
    logging.config.dictConfig(yaml_config)

logger = logging.getLogger(config_all['logging']['level'])


def get_arguments(parser):
    parser.add_argument(
        "--query",
        default="historical",
        type=str,
        required=False,
        help="'historical' gets all the data in the API, 'daily' gets the fact-checks from today",
    )

    parser.add_argument("--max_days", default=None, type=int,
                        required=False)

    return parser


def api_call(credentials, mycol, list_media, type_query, maxAgeDays=1):
    params = {'pageSize': 100}

    if type_query == 'daily':
        params['maxAgeDays'] = maxAgeDays

    for media in list_media:
        query = credentials.claims()
        request = query.search(
            reviewPublisherSiteFilter=media, **params)
        while request is not None:
            response = request.execute()
            if response:
                data = response["claims"]
                logger.info('Number of claims: {}'.format(len(data)))
                for element in data:
                    # Getting a list with one element, easier to remove the list
                    element['claimReview'] = element['claimReview'][0]
                    element['date'] = datetime.datetime.strptime(element['claimReview']['reviewDate'],
                                                                 '%Y-%m-%dT%H:%M:%S%z')
                    print(element)
                try:
                    mycol.insert_many(data, ordered=False)

                except BulkWriteError:
                    pass
                    time.sleep(5)
            request = query.search_next(request, response)


# FIXME to remove
def open_collection(new=False):
    mydb = mongo_utils.get_mongo_db()
    col_google = config_all['mongodb_params']['google']['name']
    collection = mydb[col_google]
    if collection.count_documents({}) != 0 and new is True:
        logger.info("There are entries already. Exiting")
        exit()
    return collection


def main():
    parser = argparse.ArgumentParser()
    parser = get_arguments(parser)
    args = parser.parse_args()
    logger.info('Arguments passed: {}'.format(args))
    google_credentials_key = google_credentials['GOOGLE_API_KEY']
    list_media = config_all['api_google_params']['list_media']
    factCheckService = build(
        "factchecktools", "v1alpha1", developerKey=google_credentials_key
    )
    api_params = config_all['api_google_params']
    api_type_query = api_params['type_query']
    api_max_days = api_params['max_age_days']

    if args.query:
        type_query = args.query
    else:
        type_query = api_type_query

    if args.max_days:
        max_days = args.max_days
    else:
        max_days = api_max_days

    if type_query == "historical":
        collection = open_collection(new=False)
        api_call(factCheckService, collection, list_media, type_query)

    elif type_query == "daily":
        collection = open_collection(new=False)
        api_call(factCheckService, collection, list_media,
                 type_query, maxAgeDays=max_days)


if __name__ == "__main__":
    main()
