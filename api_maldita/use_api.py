
import requests
import argparse
import json
import os
import pymongo
import importlib.util
spec = importlib.util.spec_from_file_location("credentials", os.getcwd()+"/credentials.py")
credentials = importlib.util.module_from_spec(spec)
spec.loader.exec_module(credentials)
maldita_credentials = credentials.maldita_credentials

def get_arguments(parser):
    parser.add_argument("--query", default='historical', type=str, required=False, help='\'historical\' gets all the data in the API, \'today\' gets the fact-checks from today')
    return parser

def historical_call(user, key):
    myclient = pymongo.MongoClient('mongodb://127.0.0.1:27017/iberifier')
    mydb = myclient.get_default_database()  # normalmente iberifier
    mycol = mydb["maldita"]
    if mycol.count_documents({}) != 0:
        print('There are entries already.')
        exit()
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


def main():
    parser = argparse.ArgumentParser()
    parser = get_arguments(parser)
    args = parser.parse_args()
    print(args)

    user, key = maldita_credentials()

    if args.query == 'historical':
        historical_call(user, key)

    # TODO: add the option of retrieving the data daily

if __name__ == '__main__':
    main()