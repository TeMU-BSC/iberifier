import logging
import sys
from googleapiclient.discovery import build
import argparse
import time
import os
import yaml
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
    return parser


def insert_data(data, mycol):
    """
    """
    for element in data:
        element['date'] = datetime.datetime.strptime(
            element['claimReview'][0]['reviewDate'], '%Y-%m-%dT%H:%M:%S%z')
    mycol.insert_many(data)
    logger.info('Resting 20 seconds.')

def historical_call(credentials, mycol, list_media):
    # queries = list(stopwords.words('spanish'))[120:] if language == 'es' else list(stopwords.words('portuguese'))
    for media in list_media:
        request = credentials.claims().search(
            reviewPublisherSiteFilter=media, pageSize=10000, languageCode="es"
        )
        response = request.execute()
        data = response["claims"]
        logger.info('Number of claims: {}'.format(len(data)))
        for element in data:
            # logger.info(element['claimReview'][0]['reviewDate'])
            element['date'] = datetime.datetime.strptime(element['claimReview'][0]['reviewDate'],
                                                         '%Y-%m-%dT%H:%M:%S%z')
        mycol.insert_many(data)
    logger.info('The 10 first posts inserted')
    for post in mycol.find().limit(10):
        logger.info(post)


def daily_call(credentials, mycol, list_media):
    # add here all the media coming from the historical data: db.google.distinct("claimReview.publisher.name");

    for media in list_media:
        logger.info('Querying: {}'.format(media))
        request = credentials.claims().search(
            reviewPublisherSiteFilter=media, maxAgeDays=3, languageCode="es"
        )
        response = request.execute()
        try:
            data = response["claims"]
            logger.info('Number of claims: {}'.format(len(data)))
            insert_data(data, mycol)
        except KeyError:
            logger.info('No claims')
            
        time.sleep(20)


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

    if args.query == "historical":
        collection = open_collection(new=True)
        historical_call(factCheckService, collection, list_media)

    elif args.query == "daily":
        collection = open_collection(new=False)
        daily_call(factCheckService, collection, list_media)


if __name__ == "__main__":
    main()
