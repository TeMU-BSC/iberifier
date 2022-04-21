from googleapiclient.discovery import build
import json
import argparse
import time
import os
import pymongo
import importlib.util
from nltk.corpus import stopwords
spec = importlib.util.spec_from_file_location("credentials", os.getcwd()+"/credentials.py")
credentials = importlib.util.module_from_spec(spec)
spec.loader.exec_module(credentials)
google_credentials = credentials.google_credentials


def get_arguments(parser):
    parser.add_argument("--query", default='historical', type=str, required=False, help='\'historical\' gets all the data in the API, \'daily\' gets the fact-checks from today')
    return parser

def historical_call(credentials, mycol):
    for language in ['es', 'pt']:
        queries = list(stopwords.words('spanish'))[120:] if language == 'es' else list(stopwords.words('portuguese'))
        for q in queries:
            print(q)
            time.sleep(120)
            request = credentials.claims().search(query=q, pageSize=1000000, languageCode=language)
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
                  'AFP Factual',
                  'Animal Político',
                  'Antena 3',
                  'Aos Fatos',
                  'ColombiaCheck',
                  'EFE Verifica - Agencia EFE',
                  'Efecto Cocuyo',
                  'El Surti',
                  'El Surtidor (Paraguay)',
                  'Europa Press',
                  'FactCheck.org',
                  'Fast Check CL',
                  'Maldita.es',
                  'Mexicana de Arte',
                  'Newtral',
                  'Polígrafo - SAPO',
                  'Política - Estadão',
                  'Telemundo',
                  'UOL',
                  'Univision',
                  'Verificado',
                  'Verificado MX',
                  'Verificat',
                  'elTOQUE'
                ]

    for media in list_media:
        time.sleep(20)
        print(media)
        request = credentials.claims().search(reviewPublisherSiteFilter=media, maxAgeDays=1)
        response = request.execute()
        try:
            data = response['claims']
            print(len(data))
            mycol.insert_many(data)
        except:
            continue

def open_collection():
    myclient = pymongo.MongoClient('mongodb://127.0.0.1:27017/iberifier')
    mydb = myclient.get_default_database()  # normalmente iberifier
    mycol = mydb["google"]
    #if mycol.count_documents({}) != 0:
    #    print('There are entries already.')
    #    exit()
    return mycol

def main():
    parser = argparse.ArgumentParser()
    parser = get_arguments(parser)
    args = parser.parse_args()
    print(args)

    factCheckService = build("factchecktools", "v1alpha1", developerKey=google_credentials())
    collection = open_collection()

    if args.query == 'historical':
        historical_call(factCheckService, collection)

    elif args.query == 'daily':
        daily_call(factCheckService, collection)

if __name__ == '__main__':
    main()