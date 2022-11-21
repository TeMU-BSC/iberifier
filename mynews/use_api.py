import csv

import requests
import os
import importlib.util
import argparse
import datetime
import time
from itertools import combinations

cred_path = os.path.join(os.path.dirname(__file__), "../credentials.py")
spec = importlib.util.spec_from_file_location("credentials", cred_path)
credentials = importlib.util.module_from_spec(spec)
spec.loader.exec_module(credentials)
mynews_credentials = credentials.mynews_credentials

import sys

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from mongo_utils import mongo_utils

def get_arguments(parser):
    parser.add_argument("--max", default="0", type=str, required=False, help="0 returns only the num. of outputs to the query, auto takes into account num. of factchecks")
    parser.add_argument("--type_query", default="pairs", type=str, required=False,
                        help="Indicates how to build the query. Options are: 'pairs', 'restrictive', 'triples ")
    parser.add_argument("--query", default=None, type=str, required=False, help="the tokens to query, it does not make sense if --auto_query is selected")
    parser.add_argument("--topic", default="13", type=str, required=False, help='the topic of the news, it does not make sense if --auto_query is selected')
    parser.add_argument("--time_window", default=7, type=int, required=False,
                        help='Look for news X days before the fact-check.')
    return parser

def get_token():
    public_key, password = mynews_credentials()
    files = {
        'public_key': (None, public_key),
        'password': (None, password),
    }
    TOKEN = requests.post('https://api.mynews.es/api/token/', files=files)
    return TOKEN

def query(query_expression, token, max_news, media, time_window, claim_date):
    # query the news from X days before claim date to X days after claim date
    end = claim_date + datetime.timedelta(days=time_window)
    start = claim_date - datetime.timedelta(days=time_window)
    end_int = time_to_int(end)
    start_int = time_to_int(start)

    headers = {
        'Authorization': f"Bearer {token.text}",
    }
    publications = []
    for m in media:
        publications.append(('publications', (None, m)))

    files = [
        ('query', (None, query_expression)),
        ('fromTime', (None, start_int)),
        ('toTime', (None, end_int)),
        ('maxResults', (None, max_news)),
        ('relevance', (None, 80)),
        ('extraField', (None, "Ref"))
    ]

    extended = files + publications

    response = requests.post('https://api.mynews.es/api/hemeroteca/', headers=headers, files=extended)

    return response.json()


def get_keywords(args, db, type_keywords='keywords_pairs'):
    dict_keywords = {}
    collection = 'keywords'
    limit_day = datetime.datetime.today() - datetime.timedelta(days=args.time_window)
    # get the keywords of the news older than 7 days and with no search_mynews_key
    search = {"date":{'$lt': limit_day}, "search_mynews_key": {'$exists': False}}
    cursor = db[collection].find(search)
    for fact in cursor:
        dict_keywords[(fact['_id'], collection)] = [fact[type_keywords], fact['date']]
    return dict_keywords


def time_to_int(dateobj):
    total = int(dateobj.strftime('%S'))
    total += int(dateobj.strftime('%M')) * 60
    total += int(dateobj.strftime('%H')) * 60 * 60
    total += (int(dateobj.strftime('%j')) - 1) * 60 * 60 * 24
    total += (int(dateobj.strftime('%Y')) - 1970) * 60 * 60 * 24 * 365
    return total

def write_query(keys_all, type_strategy='pairs'):
    keys=keys_all[0][:4] # I limit the keywords to 4
    claim_date = keys_all[1]
    query = ''
    previous_pair = None
    for k in keys:
        string = ''
        if type_strategy == "pairs":
            string = '(' + k[0] + ' AND ' + k[1] + ') OR '
        elif type_strategy == "restrictive":
            if not previous_pair:
                string = '(' + k[0] + ' AND ' + k[1] + ') OR '
            else:
                string = '(' + k[0] + ' AND ' + k[1] + ') AND ('+ previous_pair[0] + ' AND ' + previous_pair[1] + ') OR '
            previous_pair = k
        query += string
    if type_strategy == "triples":
        comb = combinations(keys, 3)
        for c in comb:
            string = '(' + c[0] + ' AND ' + c[1] + ' AND ' + c[2] + ') OR '
            query += string

    query = query[:-4]
    return query, claim_date

def main():
    parser = argparse.ArgumentParser()
    parser = get_arguments(parser)
    args = parser.parse_args()
    print(args)

    db = mongo_utils.get_mongo_db()

    # look for the fact-checks of a certain time span and extract the tokens
    if args.type_query in ['pairs', 'restrictive']:
        keywords = get_keywords(args, db, type_keywords='keywords_pairs')
    else:
        keywords = get_keywords(args, db, type_keywords='keywords')

    # limit news per
    print('Looking for news about {} factchecks'.format(len(keywords)))
    if args.max == 'auto':
        max_news = 100/len(keywords)
        max_news = str(int(max_news))
    else:
        max_news = int(args.max)

    # load media list
    with open('mynews/matching_list.csv') as f:
        reader = csv.reader(f)
        media = []
        for line in reader:
            media.append(line[0])

    # create the query with the "(BSC AND BARCELONA) OR (BSC AND MADRID)" format and the timespan
    mynews = db['mynews']
    token = get_token()

    n_results = 0
    for ids, keys in keywords.items():
        query_expression, claim_date = write_query(keys, type_strategy=args.type_query)
        print(query_expression)
        result = query(query_expression, token, max_news, media, args.time_window, claim_date)
        print(result)

        if result == {'detail': 'Too many requests, wait 1h'}:
            print('Rate limit, wait 1 hour.')
            time.sleep(3660)
        elif len(result['news']) != 0:
            total = result['total']
            news = result['news']
            print('Results found:',len(news))
            n_results += len(news)
            for n in news:
                n['related_to'] = ids[0]
                n['related_to_source'] = ids[1]
                n['date'] = datetime.datetime.strptime(n['Date'], '%d/%m/%Y')
                n['query_output'] = total
            mynews.insert_many(news)

    #if n_results < 100:
    #    print('rerun')


if __name__ == "__main__":
    main()
