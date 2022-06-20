
import sys
import os
import argparse

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from mongo_utils import mongo_utils
from bson.objectid import ObjectId

from datetime import datetime, timedelta
from sentence_transformers import SentenceTransformer, util

# Logging options
import logging

logger_level = "DEBUG"

logger = logging.getLogger(__name__)
logger_set_level = getattr(logging, logger_level)
logger.setLevel(logger_set_level)
formatter = logging.Formatter("%(asctime)s :: %(levelname)s :: %(name)s :: %(message)s")

def get_arguments(parser):
    parser.add_argument("--claim", default=None, type=str, required=False, help='give the id of a particular claim')
    parser.add_argument("--source", default='telegram', type=str, required=False,
                        help='Fuente dónde estamos buscando textos relacionados: twitter_test, telegram, mynews, menéame or lusa')
    parser.add_argument("--threshold", default=0.3, type=float, required=False,
                        help='Threshold of similarity.')
    parser.add_argument("--timeframe", default=7, type=int, required=False,
                        help='Up and down timeframe from the day of the claim.')
    return parser

def select_messages_timeframe(time, messages, timeframe, source):
    #time = datetime.strptime(time, "%Y-%m-%dT%H:%M:%S%z")
    x = time - timedelta(days=timeframe)
    y = time + timedelta(days=timeframe)
    selection = list(messages.find({source['date']: {'$gt': x, '$lt': y}}))
    return selection

def mbert_vectorizer(text, model):
    # Compute embedding for both lists
    vector = model.encode(text, convert_to_tensor=True)
    return vector

def vectorize_claim(claim, model):
    text = claim['text']
    vector = mbert_vectorizer(text, model)
    return vector

def vectorize_messages(messages, model, source):
    vectors = []
    for m in messages:
        vector = mbert_vectorizer(m[source['text']], model)
        vectors.append(vector)
    return vectors

def similarity_calculation(vec_1, vec_2):
    sim = util.pytorch_cos_sim(vec_1, vec_2)
    #print(sim)
    return sim

def similar_messages(c_vec, m_vecs, threshold):
    similar_messages = []
    for i, m in enumerate(m_vecs):
        sim = similarity_calculation(c_vec, m)
        if sim > threshold:
            similar_messages.append(i)
    return similar_messages

def get_source_keys(source):
    '''Defines the right fields for each source'''
    source_keys = {}
    if source == 'telegram':
        source_keys['date'] = 'date'
        source_keys['text'] = 'message'
    elif source == 'twitter_test':
        source_keys['date'] = 'created_at'
        source_keys['text'] = 'text'
    elif source == 'lusa':
        source_keys['date'] = 'date'
        source_keys['text'] = 'headline'
    return source_keys

def main():
    parser = argparse.ArgumentParser()
    parser = get_arguments(parser)
    args = parser.parse_args()
    print(args)

    # connect to the mongo db
    logger.info("Connecting to the db")
    db_iberifier = mongo_utils.get_mongo_db()

    # look for one claim in the fact-check database
    collection_maldita = db_iberifier['maldita']
    if args.claim:
        claim = collection_maldita.find_one({"_id": ObjectId(args.claim)})
    else:
        claim = collection_maldita.find_one({'date': {'$gt': datetime(2021, 11, 1), '$lt': datetime(2021, 11, 30)}}) # I can't check Lusa until maldita has a datetime type
    print(claim)

    # TODO: make functions for each data source: telegram, twitter, LUSA and menéame, mynews (for the last to get the data)
    # get all the messages from the source
    if args.source == 'telegram':
        db_telegram = mongo_utils.get_mongo_db('telegram_observer')
        collection_messages = db_telegram['messages']
        source_keys = get_source_keys(args.source)
    else:
        collection_messages = db_iberifier[args.source]
        if len(list(collection_messages.find())) == 0:
            print('This data does not exist, we currently have the collections:') # TODO: show iberifier collections
            exit()
        else:
            source_keys = get_source_keys(args.source)

    # TODO: all sources should have a date field that is in datetime format. Missing: google
    # get the messages in the time frame surrounding the claim
    messages_in_frame = select_messages_timeframe(claim['date'], collection_messages, args.timeframe, source_keys)
    print(len(messages_in_frame))
    #for i in messages_in_frame:
    #    print(i)

    # evaluate how close the messages are and assess the threshold of similarity
    model = SentenceTransformer('AIDA-UPM/mstsb-paraphrase-multilingual-mpnet-base-v2')
    c_vec = vectorize_claim(claim, model)
    m_vecs = vectorize_messages(messages_in_frame, model, source_keys)
    threshold = args.threshold
    relevant_indices = similar_messages(c_vec, m_vecs, threshold)
    print(len(relevant_indices))

    for i, m in enumerate(messages_in_frame):
        if i in relevant_indices:
            print(m[source_keys['text']])


if __name__ == '__main__':
    main()