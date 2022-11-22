import sys
import csv
import yaml

import requests
import os
import importlib.util
import argparse
import datetime
import time
import random
import tqdm
import logging.config

import logging
from itertools import combinations

# cred_path = os.path.join(os.path.dirname(__file__), "../credentials.py")
# spec = importlib.util.spec_from_file_location("credentials", cred_path)
# credentials = importlib.util.module_from_spec(spec)
# spec.loader.exec_module(credentials)
# mynews_credentials = credentials.mynews_credentials


sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from mongo_utils import mongo_utils

logger = logging.getLogger(__name__)

# Load config and credentials

config_path = os.path.join(os.path.dirname(
    __file__), '../config', 'config.yaml')
config_all = yaml.safe_load(open(config_path))


logging_config_path = os.path.join(os.path.dirname(
    __file__), '../config', config_all['logging']['logging_filename'])
with open(logging_config_path,  "r") as f:
    yaml_config = yaml.safe_load(f.read())
    logging.config.dictConfig(yaml_config)

logger = logging.getLogger(config_all['logging']['level'])


mynews_cred_path = os.path.join(
    os.path.dirname(__file__),
    "../config",
    config_all["api_mynews_params"]["cred_filename"],
)
mynews_credentials = yaml.safe_load(open(mynews_cred_path))[
    "mynews_api_credentials"]


def get_arguments(parser):
    parser.add_argument("--max", default=None, type=str, required=False,
                        help="0 returns only the num. of outputs to the query, auto takes into account num. of factchecks")
    parser.add_argument("--type_query", default=None, type=str, required=False,
                        help="Indicates how to build the query. Options are: 'pairs', 'restrictive', 'triples ")
    parser.add_argument("--query", default=None, type=str, required=False,
                        help="the tokens to query, it does not make sense if --auto_query is selected")
    parser.add_argument("--topic", default=None, type=str, required=False,
                        help='the topic of the news, it does not make sense if --auto_query is selected')
    return parser


def get_token(public_key, password):
    files = {
        'public_key': (None, public_key),
        'password': (None, password),
    }
    TOKEN = requests.post('https://api.mynews.es/api/token/', files=files)
    return TOKEN


def query(query_expression, token, max_news, media, claim_date, days_before, days_after):
    # query the news from X days before claim date to X days after claim date
    end = claim_date + datetime.timedelta(days=days_after)
    start = claim_date - datetime.timedelta(days=days_before)
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

    response = requests.post(
        'https://api.mynews.es/api/hemeroteca/', headers=headers, files=extended)

    return response.json()


def get_lists_ids(db,
                  col_keywords,
                  keywords_key,
                  search_mynews_key,
                  max_claims_per_day,
                  days_before,
                  days_after):
    limit_day = datetime.datetime.today() - datetime.timedelta(days=days_after)
    aggregate_query = [
        {
            "$match": {
                "$and": [
                    {search_mynews_key: {'$exists': False}},
                    {keywords_key: {'$exists': True}},
                    {'date': {'$lt': limit_day}}
                ]
            },

        },
        {
            "$project": {
                "_id": 1
            }
        }
    ]
    results = [i['_id'] for i in db[col_keywords].aggregate(aggregate_query)]

    if max_claims_per_day:
        return random.sample(results, max_claims_per_day)
    return results


def get_documents(db, col_keywords, keywords_key,
                  search_mynews_key, max_claims_per_day, max_news_per_claim,
                  days_before, days_after):

    global max_news
    list_ids = get_lists_ids(db,
                             col_keywords,
                             keywords_key=keywords_key,
                             search_mynews_key=search_mynews_key,
                             max_claims_per_day=max_claims_per_day,
                             days_before=days_before, days_after=days_after)

    tqdm_length = len(list_ids)

    if max_news_per_claim == 'auto':
        max_news = 100/tqdm_length
        max_news = str(int(max_news))
    else:
        max_news = int(max_news_per_claim)
    cursor = db[col_keywords].find({'_id': {"$in": list_ids}}, batch_size=1)

    for record in tqdm.tqdm(cursor, total=tqdm_length):
        yield record
    cursor.close()


def get_keywords(args, db, type_keywords='keywords_pairs'):
    dict_keywords = {}
    collection = 'keywords'
    limit_day = datetime.datetime.today() - datetime.timedelta(days=args.time_window)
    # get the keywords of the news older than 7 days and with no search_mynews_key
    search = {"date": {'$lt': limit_day},
              "search_mynews_key": {'$exists': False}}
    cursor = db[collection].find(search)
    for fact in cursor:
        dict_keywords[(fact['_id'], collection)] = [
            fact[type_keywords], fact['date']]
    return dict_keywords


def time_to_int(dateobj):
    total = int(dateobj.strftime('%S'))
    total += int(dateobj.strftime('%M')) * 60
    total += int(dateobj.strftime('%H')) * 60 * 60
    total += (int(dateobj.strftime('%j')) - 1) * 60 * 60 * 24
    total += (int(dateobj.strftime('%Y')) - 1970) * 60 * 60 * 24 * 365
    return total


def write_query(keywords, keywords_limit=4, type_strategy='pairs'):
    keys = keywords[:keywords_limit]  # I limit the keywords to 4
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
                string = '(' + k[0] + ' AND ' + k[1] + ') AND (' + \
                    previous_pair[0] + ' AND ' + previous_pair[1] + ') OR '
            previous_pair = k
        query += string
    if type_strategy == "triples":
        comb = combinations(keys, 3)
        for c in comb:
            string = '(' + c[0] + ' AND ' + c[1] + ' AND ' + c[2] + ') OR '
            query += string

    # Is it to be linked to the keywords limit too?
    query = query[:-keywords_limit]
    return query


def main():
    parser = argparse.ArgumentParser()
    parser = get_arguments(parser)
    args = parser.parse_args()
    logger.info(args)

    db = mongo_utils.get_mongo_db()
    col_keywords = config_all['mongodb_params']['keywords']['name']
    col_mynews = config_all['mongodb_params']['mynews']['name']

    api_key = mynews_credentials['public_key']
    api_password = mynews_credentials['password']

    mynews_url = config_all['api_mynews_params']['root_url']
    search_mynews_key = config_all['api_mynews_params']['search_mynews_key']
    mynews_search_params = config_all['api_mynews_params']['search_params']
    max_claims_per_day = mynews_search_params['max_claims_per_day']
    max_news_per_claim = mynews_search_params['max_news_per_claim']
    days_before = mynews_search_params['days_before']
    days_after = mynews_search_params['days_after']
    type_query = mynews_search_params['type_query']
    keywords_limit = mynews_search_params['keywords_limit']

    # look for the fact-checks of a certain time span and extract the tokens
    if args.type_query:
        type_query = args.type_query

    if type_query in ['pairs', 'restrictive']:
        strategy = 'keywords_pairs'
    else:
        strategy = 'keywords'

    # limit news per
    if args.max:
        max_news_per_claim = args.max

    # load media list
    with open('mynews/matching_list.csv') as f:
        reader = csv.reader(f)
        media = []
        for line in reader:
            media.append(line[0])

    # create the query with the "(BSC AND BARCELONA) OR (BSC AND MADRID)" format and the timespan
    token = get_token(api_key, api_password)

    n_results = 0
    sources_to_update = []

    for doc in get_documents(db,
                             col_keywords=col_keywords,
                             keywords_key=strategy,
                             search_mynews_key=search_mynews_key,
                             max_claims_per_day=max_claims_per_day,
                             max_news_per_claim=max_news_per_claim,
                             days_before=days_before,
                             days_after=days_after):
        fact_id = doc['fact_id']
        claim_date = doc['date']
        keyword_search = doc[strategy]

        query_expression = write_query(
            keyword_search,
            keywords_limit=keywords_limit,
            type_strategy=type_query
        )
        logger.debug(query_expression)
        result = query(query_expression, token, max_news,
                       media, claim_date,
                       days_before=days_before,
                       days_after=days_after
                       )
        logger.info(result)

        print('', result['total'])
        print(len(result['news']))

        if result == {'detail': 'Too many requests, wait 1h'}:
            logger.debug('Rate limit, wait 1 hour.')
            time.sleep(3660)
        elif len(result['news']) != 0:
            total = result['total']
            news = result['news']
            logger.debug('Results found:', len(news))
            n_results += len(news)
            for n in news:
                n['fact_id'] = fact_id
                n['date'] = datetime.datetime.strptime(n['Date'], '%d/%m/%Y')
                n['query_output'] = total
            db[col_mynews].insert_many(news)

        sources_to_update.append(fact_id)

    db[col_keywords].update_many(
        {"fact_id": {"$in": sources_to_update}}, {
            "$set": {search_mynews_key: datetime.datetime.now()}}
    )


if __name__ == "__main__":
    main()
