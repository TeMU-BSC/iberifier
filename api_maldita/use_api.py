import requests
import argparse
import os
import yaml
import datetime
import logging
import logging.config
import time

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


def api_call(user, key, api_url, type_query, mycol):

    params = {'page': 1, 'itemPerPage': 30}
    if type_query == 'historical':
        pass
    elif type_query == 'daily':
        yesterday = datetime.datetime.now() - datetime.timedelta(days=1)
        date_yesterday = yesterday.strftime("%Y-%m-%d")
        date_today = datetime.datetime.now().strftime("%Y-%m-%d")
        params['createdAt[strictly_after]'] = date_yesterday
    else:
        raise Exception(
            'Need to get a proper type of query: Either historical or daily')

    while True:
        response = requests.get(
            api_url, params=params, auth=requests.auth.HTTPBasicAuth(user, key))
        params['page'] += 1
        data = response.json()
        if data == []:
            break
        for element in data:
            element['date'] = datetime.datetime.strptime(
                element['createdAt'], '%Y-%m-%dT%H:%M:%S%z')
        mycol.insert_many(data)
        time.sleep(1)
    logging.debug('10th posts')
    for post in mycol.find().limit(10):
        logging.debug(post)


def open_collection(col_name):
    mydb = mongo_utils.get_mongo_db()
    mycol = mydb[col_name]

    return mycol


def main():
    logging.info('Starting to collect maldita claims')
    parser = argparse.ArgumentParser()
    parser = get_arguments(parser)
    args = parser.parse_args()
    logging.info(f'Arguments passed: {args}')

    col_maldita = config_all['mongodb_params']['maldita']['name']
    collection = open_collection(col_maldita)
    api_user = maldita_credentials['MALDITA_API_USER']
    api_key = maldita_credentials['MALDITA_API_KEY']
    api_url = config_all['api_maldita_params']['root_url']
    collection = open_collection(col_maldita)

    api_call(api_user, api_key, api_url, args.query, collection)


if __name__ == "__main__":
    main()
