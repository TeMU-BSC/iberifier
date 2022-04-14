from googleapiclient.discovery import build
import json
import argparse
import time
import os
import pymongo
import importlib.util
spec = importlib.util.spec_from_file_location("credentials", os.getcwd()+"/credentials.py")
credentials = importlib.util.module_from_spec(spec)
spec.loader.exec_module(credentials)
google_credentials = credentials.google_credentials


def get_arguments(parser):
    parser.add_argument("--query", default='historical', type=str, required=False)
    return parser

def historical_call(credentials):
    myclient = pymongo.MongoClient('mongodb://127.0.0.1:27017/iberifier')
    mydb = myclient.get_default_database()  # normalmente iberifier
    mycol = mydb["google"]
    #if mycol.count_documents({}) != 0:
    #    print('There are entries already.')
    #    exit()
    all_letters = 'abcdefghijklmnopqrstuvwxyz'
    for language in ['es', 'pt']:
        # todo: pensar otra estrategia, creo que solo coge claims que contengan la letra aisaldamente como palabra
        for letter in all_letters:
            time.sleep(60)
            request = credentials.claims().search(query=letter, pageSize=1000000, languageCode=language)
            response = request.execute()
            try:
                data = response['claims']
                print(data)
                mycol.insert_many(data)
            except:
                continue
    for post in mycol.find().limit(10):
        print(post)


def main():
    parser = argparse.ArgumentParser()
    parser = get_arguments(parser)
    args = parser.parse_args()
    print(args)

    factCheckService = build("factchecktools", "v1alpha1", developerKey=google_credentials())

    if args.query == 'historical':
        historical_call(factCheckService)

    # todo: dar opción de recoger las claims diarias

if __name__ == '__main__':
    main()