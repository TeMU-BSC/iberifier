import yaml
import argparse
import logging
import os
import sys

import logging.config


sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from mongo_utils import mongo_utils

config_path = os.path.join(os.path.dirname(
    __file__), '../config', 'config.yaml')
config_all = yaml.safe_load(open(config_path))

logging_config_path = os.path.join(os.path.dirname(
    __file__), '../config', config_all['logging']['logging_filename'])
with open(logging_config_path,  "r") as f:
    yaml_config = yaml.safe_load(f.read())
    logging.config.dictConfig(yaml_config)

logger = logging.getLogger(config_all['logging']['level'])


def get_arguments(parser):
    parser.add_argument("--rerun", action='store_true',
                        help="rerun the keywords generation")
    parser.add_argument("--time_window", default=None,
                        type=int, help="Number of days to compute")
    parser.add_argument("--co_threshold", default=None, type=int,
                        help="Number of cooccurrencies threshold")
    parser.add_argument("--max_words", default=None,
                        type=int, help="Maximum number of keywords")
    return parser


def update_fact(
    db,
    collection,
    id_,
    keywords,
    keywords_pairs,
):
    db[collection].update_one(
        {"_id": id_},
        {
            "$set": {
                "keywords": keywords,
                "keywords_pairs": keywords_pairs,
            }
        },
    )


def check_cooccurrency(keywords, db, col_dict):
    return bool(db[col_dict].find_one({"words": {"$all": list(keywords)}}, {"_id": 0}))


def delete_from_cooccurrency(keywords_list, db, col_dict):
    try:
        for pairs in list(
            keywords_list
        ):  # Need to create a copy of it to delete while looping
            if check_cooccurrency(pairs, db, col_dict):
                keywords_list.remove(pairs)
        return keywords_list
    except TypeError:  # Empty list
        raise Exception(
            "Issue with removing words from cooccurrency, probably empty list of keywords"
        )


def getting_records(db, collection, rerun):
    if rerun:
        search = {}
    else:
        search = {"keywords": {"$exists": False}}
    # if args.time_window:
    #     today = datetime.today()
    #     days_ago = today - timedelta(days=args.time_window)
    #     search["date"] = {'$gt': days_ago, '$lt': today}
    cursor = db[collection].find(search, batch_size=1)
    #print('emtpy cursor?')
    for record in cursor:
        #print('no')
        yield record


def create_and_filter_pairs(db, keywords, threshold):
    filtered_pairs = []
    pairs = ((x, y) for x in keywords for y in keywords if y > x)
    for pair in pairs:
        # filter pairs that are too co-occurring
        check = [x.lower() for x in pair]
        check.sort()
        cursor = db["cooccurrence"].find({'words': check})
        for item in cursor:
            if item:
                if item['counts'] > threshold:
                    continue
        filtered_pairs.append(pair)
    return filtered_pairs


def remove_nonalpha(strings):
    new = []
    for s in strings:
        new.append(''.join(x for x in s if x.isalpha()))
    new = list(set([n for n in new if n != '']))
    return new


def strategy_one(db, record, max_words, threshold):

    content_ner = list()
    for key in ['ner_review', 'ner_claim']:
        try:
            for entity in record[key]:
                content_ner.append(record[key][entity][0])
        except KeyError:
            pass
    content_pos_noun = list()
    content_pos_adj = list()
    content_pos_verb = list()
    for key in ['pos_review', 'pos_claim']:
        try:
            content_pos_noun.extend(record[key]['NOUN'])
        except KeyError:
            pass
        try:
            content_pos_adj.extend(record[key]['ADJ'])
        except KeyError:
            pass
        try:
            content_pos_verb.extend(record[key]['VERB'])
        except KeyError:
            pass

    keywords = []
    keywords_pairs = []
    if len(keywords) < 3:
        keywords += content_ner

    if len(keywords) < 3:
        # content_pos = remove_nonalpha(content_pos)
        keywords += remove_nonalpha(content_pos_noun)
    if len(keywords) < 3:
        keywords += remove_nonalpha(content_pos_adj)
    if len(keywords) < 3:
        # verbs = remove_nonalpha(verbs)
        keywords += remove_nonalpha(content_pos_verb)

    keywords = list(set(keywords))
    if len(keywords) > max_words:
        keywords = keywords[:max_words]
    keywords.sort()

    if len(keywords) == 0:
        logger.debug(f"{record['_id']}empty example")
    else:
        keywords_pairs = create_and_filter_pairs(db, keywords, threshold)

    return keywords, keywords_pairs

def strategy_two(record, max_words):
    '''
    This strategy looks for NER in claim and NER in review. Then, if less than 6 keywords, it looks for the frist NOUN of the claim,
    the first verb of the claim, and the first adjective of the claim until it has 6 keywords.
    '''
    print(record['claim'])

    keywords = list()
    for key in ['ner_claim', 'ner_review']:
        try:
            for entity in record[key]:
                keywords.append(record[key][entity][0])
        except KeyError:
            pass

    i = 0
    while len(keywords) < max_words:

        key = 'pos_claim'
        try:
            keywords.append(record[key]['NOUN'][i])
        except (KeyError, IndexError):
            pass
        try:
            keywords.append(record[key]['ADJ'][i])
        except (KeyError, IndexError):
            pass
        try:
            keywords.append(record[key]['VERB'][i]) # TODO: delete non-expresive verbs
        except (KeyError, IndexError):
            pass
        i += 1

        keywords = remove_nonalpha(keywords)
        keywords = list(set(keywords))
        if i == 3:
            break

    if len(keywords) > max_words:
        keywords = keywords[:max_words]
    #else:
    #    keywords = content_ner
    print(keywords)

    keywords.sort()

    keywords_pairs = [] # we are not going to use this in the end
    # if len(keywords) == 0:
    #     logger.debug(f"{record['_id']}empty example")
    # else:
    #     keywords_pairs = create_and_filter_pairs(db, keywords, threshold)

    return keywords, keywords_pairs


def main():
    parser = argparse.ArgumentParser()
    parser = get_arguments(parser)
    args = parser.parse_args()

    # DB Connection
    logger.info("Connecting to the db")
    db = mongo_utils.get_mongo_db()
    logger.info("Connected to: {}".format(db))

    col_keywords = config_all['mongodb_params']['keywords']['name']
    keywords_params = config_all['keywords_params']
    config_max_words = keywords_params['max_words']
    config_co_threshold = keywords_params['co_threshold']
    config_rerun = keywords_params['rerun']

    if args.max_words:
        max_words = args.max_words
    else:
        max_words = config_max_words

    if args.co_threshold:
        co_threshold = args.co_threshold
    else:
        co_threshold = config_co_threshold
    if args.rerun:
        rerun = args.rerun
    else:
        rerun = config_rerun

    for record in getting_records(db, col_keywords, rerun):

        #keywords, keywords_pairs = strategy_one(
        #    db, record, max_words=max_words, threshold=co_threshold)
        keywords, keywords_pairs = strategy_two(
            record, max_words=max_words)

        update_fact(
            db,
            col_keywords,
            record['_id'],
            keywords,
            keywords_pairs,
        )


if __name__ == "__main__":
    main()
