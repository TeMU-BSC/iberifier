
import requests
import os
import importlib.util
import argparse
import datetime
import time

cred_path = os.path.join(os.path.dirname(__file__), "../credentials.py")
spec = importlib.util.spec_from_file_location("credentials", cred_path)
credentials = importlib.util.module_from_spec(spec)
spec.loader.exec_module(credentials)
mynews_credentials = credentials.mynews_credentials

import sys

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from mongo_utils import mongo_utils

def get_arguments(parser):
    parser.add_argument("--auto_query", action='store_true', help="The queries will be generated automatically from the fact-checks of that time span")
    parser.add_argument("--fromD", default=None, type=str, required=False) #"1654321118"
    parser.add_argument("--toD", default=None, type=str, required=False) #"1656913073"
    parser.add_argument("--max", default="2", type=str, required=False)
    parser.add_argument("--query", default="(BSC AND BARCELONA) OR (BSC AND MADRID)", type=str, required=False,
                        help="the tokens to query, it does not make sense if --auto_query is selected")
    parser.add_argument("--topic", default="13", type=str, required=False, help='the topic of the news, it does not make sense if --auto_query is selected')
    return parser

def get_token():
    public_key, password = mynews_credentials()
    files = {
        'public_key': (None, public_key),
        'password': (None, password),
    }
    TOKEN = requests.post('https://api.mynews.es/api/token/', files=files)
    return TOKEN

def query(query_expression, token, args):
    end = datetime.datetime.today()
    start = end - datetime.timedelta(days=10)
    end_int = time_to_int(end)
    start_int = time_to_int(start)

    headers = {
        'Authorization': f"Bearer {token.text}",
    }

    files = {
        'query': (None, query_expression),
        'fromTime': (None, start_int),
        'toTime': (None, end_int),
        'maxResults': (None, args.max),
    }

    response = requests.post('https://api.mynews.es/api/hemeroteca/', headers=headers, files=files)

    return response.json()

def get_keywords(args, db):
    dict_keywords = {}
    for collection in ["maldita", "google"]:
        if args.fromD: # TODO: this has to be formated the right way, right now it does not work
            end = args.fromD
            start = args.toD
        else:
            end = datetime.datetime.today()
            start = end - datetime.timedelta(days=2)
        search = {"date":{'$gt': start, '$lt': end}}
        cursor = db[collection].find(search)
        for fact in cursor:
            print(fact['text'])
            print(fact['keyword_pairs'])
            dict_keywords[fact['_id']] = fact['keyword_pairs']
    return dict_keywords


def time_to_int(dateobj):
    total = int(dateobj.strftime('%S'))
    total += int(dateobj.strftime('%M')) * 60
    total += int(dateobj.strftime('%H')) * 60 * 60
    total += (int(dateobj.strftime('%j')) - 1) * 60 * 60 * 24
    total += (int(dateobj.strftime('%Y')) - 1970) * 60 * 60 * 24 * 365
    return total

def write_query(pairs):
    query = ''
    for pair in pairs:
        string = '(' + pair[0] + ' AND ' + pair[1] + ') OR '
        query += string
    query = query[:-3]
    return query

def main():
    parser = argparse.ArgumentParser()
    parser = get_arguments(parser)
    args = parser.parse_args()
    print(args)

    db = mongo_utils.get_mongo_db()

    # look for the fact-checks of a certain time span and extract the tokens
    filtered_pairs = get_keywords(args, db)

    # create the query with the "(BSC AND BARCELONA) OR (BSC AND MADRID)" format and the timespan
    mynews = db['mynews']
    token = get_token()

    for ids, pairs in filtered_pairs.items():
        query_expression = write_query(pairs)
        print(query_expression)
        result = query(query_expression, token, args)
        print(result)
        if len(result) > 0 and not result == {'detail': 'Too many requests, wait 1h'}:
            print(type(result['news']), len(result['news']))
            mynews.insert_many(result['news'])
        elif result == {'detail': 'Too many requests, wait 1h'}:
            print('Rate limit, wait 1 hour.')
            time.sleep(3660)


    # TODO: should I limit the number of queries and max articles per month? Make the calculations


if __name__ == "__main__":
    main()
