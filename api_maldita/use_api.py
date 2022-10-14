import requests
import argparse
import os
import yaml
import datetime
import logging

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

logging.basicConfig(format='%(asctime)s %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

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
        # with open("results_{}.jsonl".format('prova'), "a") as f:
        #    f.write(json.dumps(data) + "\n")
        for element in data:
            element['date'] = datetime.datetime.strptime(
                element['createdAt'], '%Y-%m-%dT%H:%M:%S%z')
        mycol.insert_many(data)
    logging.info('10th posts')
    for post in mycol.find().limit(10):
        logging.info(post)


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
    parser = argparse.ArgumentParser()
    parser = get_arguments(parser)
    args = parser.parse_args()
    logging.info(f'Arguments passed: {args}')

    col_maldita = config_all['mongodb_params']['maldita']['name']
    collection = open_collection(col_maldita)
    api_user = maldita_credentials['MALDITA_API_USER']
    api_key = maldita_credentials['MALDITA_API_KEY']
    user, key = maldita_credentials()
    collection = open_collection()

    if args.query == "historical":
        historical_call(api_user, api_key, collection)
    elif args.query == "daily":
        daily_call(api_user, api_key, collection)


if __name__ == "__main__":
    main()
