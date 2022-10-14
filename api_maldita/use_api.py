import requests
import argparse
import os
import yaml
import datetime
import logging
import logging.config

import sys

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from mongo_utils import mongo_utils


config_path = os.path.join(os.path.dirname(
    __file__), '../config', 'config.yaml')
config_all = yaml.safe_load(open(config_path))

maldita_cred_path = os.path.join(
    os.path.dirname(__file__),
    "../config",
    config_all["api_maldita_params"]["cred_filename"],
)
maldita_credentials = yaml.safe_load(open(maldita_cred_path))[
     "maldita_api_credentials"]


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


def historical_call(user, key, mycol):
    page = 1
    while True:
        query = "https://repositorio.iberifier.eu/api/contents?page="

        params = {'page': str(page), 'itemPerPage': 30}
        response = requests.get(
            query, params=params, auth=requests.auth.HTTPBasicAuth(user, key))
        page += 1
        data = response.json()
        if data == []:
            break
        for element in data:
            element['date'] = datetime.datetime.strptime(
                element['createdAt'], '%Y-%m-%dT%H:%M:%S%z')
        mycol.insert_many(data)
    logging.debug('10th posts')
    for post in mycol.find().limit(10):
        logging.debug(post)


def daily_call(user, key, mycol):
    # get the data from the day before
    yesterday = datetime.datetime.now() - datetime.timedelta(days=1)
    string = yesterday.strftime("%Y-%m-%d")
    query = (
        "https://repositorio.iberifier.eu/api/contents?page=1&itemsPerPage=30&createdAt%5Bstrictly_after%5D="
        + string
    )
    response = requests.get(query, auth=requests.auth.HTTPBasicAuth(user, key))
    data = response.json()
    logging.info(f'Number of claims collected: {len(data)}')
    if data == []:
        pass
    else:
        for element in data:
            element['date'] = datetime.datetime.strptime(
                element['createdAt'], '%Y-%m-%dT%H:%M:%S%z')
        # print(data)
        mycol.insert_many(data)


def open_collection(col_name):
    mydb = mongo_utils.get_mongo_db()
    mycol = mydb[col_name]

    return mycol


def main():
    logging.info('test')
    parser = argparse.ArgumentParser()
    parser = get_arguments(parser)
    args = parser.parse_args()
    logging.info(f'Arguments passed: {args}')

    col_maldita = config_all['mongodb_params']['maldita']['name']
    collection = open_collection(col_maldita)
    api_user = maldita_credentials['MALDITA_API_USER']
    api_key = maldita_credentials['MALDITA_API_KEY']
    collection = open_collection(col_maldita)

    if args.query == "historical":
        historical_call(api_user, api_key, collection)
    elif args.query == "daily":
        daily_call(api_user, api_key, collection)


if __name__ == "__main__":
    main()
