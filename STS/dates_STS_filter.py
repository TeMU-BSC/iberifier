import sys
import os
import argparse
import tqdm

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from mongo_utils import mongo_utils
from bson.objectid import ObjectId

from datetime import datetime, timedelta
from sentence_transformers import SentenceTransformer, util
from sent2vec.vectorizer import Vectorizer
from scipy import spatial

# Logging options
import logging

logger_level = "DEBUG"

logger = logging.getLogger(__name__)
logger_set_level = getattr(logging, logger_level)
logger.setLevel(logger_set_level)
formatter = logging.Formatter("%(asctime)s :: %(levelname)s :: %(name)s :: %(message)s")


def get_arguments(parser):
    parser.add_argument(
        "--claim",
        default=None,
        type=str,
        required=False,
        help="give the id of a particular claim",
    )
    parser.add_argument(
        "--source",
        default="telegram",
        type=str,
        required=False,
        help="Fuente dónde estamos buscando textos relacionados: twitter_test, telegram, mynews, menéame or lusa",
    )
    parser.add_argument(
        "--threshold",
        default=0.3,
        type=float,
        required=False,
        help="Threshold of similarity.",
    )
    parser.add_argument(
        "--timeframe",
        default=15,
        type=int,
        required=False,
        help="Up and down timeframe from the day of the claim.",
    )
    parser.add_argument("--period", default=None, required=False, type=str, help="Should give the dates to look for claims, but it's not implemented.")
    parser.add_argument("--collection", default="maldita", required=False, type=str,
                        help="Collection to look from, should be maldita or google.")
    return parser


def select_messages_timeframe(time, messages, timeframe, source):
    x = time - timedelta(days=timeframe)
    y = time + timedelta(days=timeframe)
    print(time, messages, timeframe, source, x, y)
    selection = list(messages.find({source["date"]: {"$gt": x, "$lt": y}})) # also filter by related to
    return selection

def vectorize(sentences, vectorizer):
    vectorizer.run(sentences)
    vectors = vectorizer.vectors
    return vectors


# TODO: in some cases we might also be interested in the body
def get_source_keys(source):
    """Defines the right fields for each source"""
    source_keys = {}
    if source == "telegram":
        source_keys["date"] = "date"
        source_keys["text"] = "message"
    elif source == "tweets" or source == "tweets_new_call_strat":
        source_keys["date"] = "date"
        source_keys["text"] = "text"
    elif source == "lusa":
        source_keys["date"] = "date"
        source_keys["text"] = "headline"
    elif source == "mynews":
        source_keys["date"] = "date"
        source_keys["text"] = "Title"
    return source_keys

def get_list_ids(db, source, claim_id, dates_limit=False, timeframe=False):
    collection = db[source]
    if dates_limit: # TODO: this has not been tried yet
        x = dates_limit - timedelta(days=timeframe)
        y = dates_limit + timedelta(days=timeframe)
        results = list(collection.find({source["date"]: {"$gt": x, "$lt": y}}))
    else:
        results = [i['_id'] for i in collection.find({'fact_id': claim_id})]
    return results

def get_messages(db, claim, args):
    if args.source == "telegram":
        db_telegram = mongo_utils.get_mongo_db("telegram_observer")
        source_keys = get_source_keys(args.source)
        list_ids = get_list_ids(db_telegram, "messages", claim['_id'], dates_limit=claim['date'], timeframe=7)
        tqdm_length = len(list_ids)
    else:
        source_keys = get_source_keys(args.source)
        list_ids = get_list_ids(db, args.source, claim['_id'])
        tqdm_length = len(list_ids)
    cursor = db[args.source].find({'_id': {"$in": list_ids}}, batch_size=1)
    for record in tqdm.tqdm(cursor, total=tqdm_length):
        yield record, source_keys
    cursor.close()


def main():
    parser = argparse.ArgumentParser()
    parser = get_arguments(parser)
    args = parser.parse_args()
    print(args)
    method = 'SentenceTransformers'

    # connect to the mongo db
    logger.info("Connecting to the db")
    db_iberifier = mongo_utils.get_mongo_db()

    # look for one claim in the fact-check database
    collection = db_iberifier[args.collection] # google or maldita
    if args.claim:
        claim = collection.find_one({"_id": ObjectId(args.claim)})
    elif args.period:
        print('not implemented')
        exit()
    else:
        claim = collection.find_one()
    print(claim)

    # calculate the distance to all the related info
    distances = []
    texts = []
    if method == 'sent2vec':
        model = Vectorizer(pretrained_weights='PlanTL-GOB-ES/roberta-base-bne')
        print('This method does not work properly')
    else:
        model = SentenceTransformer('sentence-transformers/stsb-xlm-r-multilingual')
        #'sentence-transformers/distiluse-base-multilingual-cased')
        #'hiiamsid/sentence_similarity_spanish_es')

    for doc,source_keys in get_messages(db_iberifier, claim, args):

        if method == 'sent2vec':
            # c_vec = vectorize([claim['text']], model)[0]
            # m_vec = vectorize([doc[source_keys['text']]], model)[0]
            # dist_1 = spatial.distance.cosine(c_vec, m_vec)
            # dist_2 = spatial.distance.cosine(c_vec, m_vec)
            # print('dist_1: {0}, dist_2: {1}'.format(dist_1, dist_2))
            print('This method does not work properly')
            exit()

        if method == 'SentenceTransformers':
            embeddings = model.encode([claim['text'], doc[source_keys['text']]])
            dist = spatial.distance.cosine(embeddings[0], embeddings[1])
            distances.append(dist)
            texts.append(doc[source_keys['text']])

    print('\n TOP RELATED:')
    indexes = [i[1] for i in sorted([(x, i) for (i, x) in enumerate(distances)])][:5]
    for val in indexes:
        print(texts[val], distances[val])

    print('\n TOP NOT RELATED:')
    indexes = [i[1] for i in sorted([(x, i) for (i, x) in enumerate(distances)])[-5:]]
    for val in indexes:
        print(texts[val], distances[val])


if __name__ == "__main__":
    main()
