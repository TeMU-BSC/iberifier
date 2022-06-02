
import requests
import argparse
import os
import datetime
import importlib.util
spec = importlib.util.spec_from_file_location("credentials", os.getcwd()+"/credentials.py")
credentials = importlib.util.module_from_spec(spec)
spec.loader.exec_module(credentials)
maldita_credentials = credentials.maldita_credentials

import sys
sys.path.insert(1,'/home/Life/iberifier/iberifier')
from mongo_utils import mongo_utils

def get_arguments(parser):
    parser.add_argument("--query", default='historical', type=str, required=False, help='\'historical\' gets all the data in the API, \'daily\' gets the fact-checks from today')
    return parser

def historical_call(user, key, mycol):
    page = 1
    while True:
        query = 'https://repositorio.iberifier.eu/api/contents?page='+str(page)+'&itemsPerPage=30'
        response = requests.get(query, auth=requests.auth.HTTPBasicAuth(user, key))
        page += 1
        data = response.json()
        if data == []:
            break
        #with open("results_{}.jsonl".format('prova'), "a") as f:
        #    f.write(json.dumps(data) + "\n")
        mycol.insert_many(data)
    for post in mycol.find().limit(10):
        print(post)

def daily_call(user, key, mycol):
    # get the data from the day before
    yesterday = datetime.datetime.now()- datetime.timedelta(days=1)
    string = yesterday.strftime('%Y-%m-%d')
    query = 'https://repositorio.iberifier.eu/api/contents?page=1&itemsPerPage=30&createdAt%5Bstrictly_after%5D='+string
    response = requests.get(query, auth=requests.auth.HTTPBasicAuth(user, key))
    data = response.json()
    print(len(data))
    if data == []:
        pass
    else:
        mycol.insert_many(data)

def open_collection():
    mydb = mongo_utils.get_mongo_db()
    mycol = mydb["maldita"]

    return mycol


def main():
    parser = argparse.ArgumentParser()
    parser = get_arguments(parser)
    args = parser.parse_args()
    print(args)

    user, key = maldita_credentials()
    collection = open_collection()

    if args.query == 'historical':
        historical_call(user, key, collection)
    elif args.query == 'daily':
        daily_call(user, key, collection)

if __name__ == '__main__':
    main()