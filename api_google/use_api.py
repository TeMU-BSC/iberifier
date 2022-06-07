from googleapiclient.discovery import build
import argparse
import time
import os
import importlib.util
from nltk.corpus import stopwords
spec = importlib.util.spec_from_file_location("credentials", os.getcwd()+"/credentials.py")
credentials = importlib.util.module_from_spec(spec)
spec.loader.exec_module(credentials)
google_credentials = credentials.google_credentials

import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from mongo_utils import mongo_utils

def get_arguments(parser):
    parser.add_argument("--query", default='historical', type=str, required=False, help='\'historical\' gets all the data in the API, \'daily\' gets the fact-checks from today')
    return parser

def historical_call(credentials, mycol):
    list_media = [
        'antena3.com',
        'europapress.es',
        'newtral.es',
    ]
    #queries = list(stopwords.words('spanish'))[120:] if language == 'es' else list(stopwords.words('portuguese'))
    for media in list_media:
        request = credentials.claims().search(reviewPublisherSiteFilter=media, pageSize=10000, languageCode='es')
        response = request.execute()
        try:
            data = response['claims']
            print(len(data))
            mycol.insert_many(data)
        except:
            continue
    for post in mycol.find().limit(10):
        print(post)

def daily_call(credentials, mycol):
    # add here all the media coming from the historical data: db.google.distinct("claimReview.publisher.name");
    list_media = [
        'antena3.com',
        'europapress.es',
        'newtral.es',
    ]

    for media in list_media:
        time.sleep(20)
        print(media)
        request = credentials.claims().search(reviewPublisherSiteFilter=media, maxAgeDays=1, languageCode='es')
        response = request.execute()
        try:
            data = response['claims']
            print(len(data))
            mycol.insert_many(data)
        except:
            continue

def open_collection(new=False):
    mydb = mongo_utils.get_mongo_db()
    mycol = mydb["google"]
    if mycol.count_documents({}) != 0 and new==True:
        print('There are entries already.')
        exit()
    return mycol

def main():
    parser = argparse.ArgumentParser()
    parser = get_arguments(parser)
    args = parser.parse_args()
    print(args)

    factCheckService = build("factchecktools", "v1alpha1", developerKey=google_credentials())

    if args.query == 'historical':
        collection = open_collection(new=True)
        historical_call(factCheckService, collection)

    elif args.query == 'daily':
        collection = open_collection(new=False)
        daily_call(factCheckService, collection)

if __name__ == '__main__':
    main()