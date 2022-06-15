
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
print(os.path.dirname(__file__))
from mongo_utils import mongo_utils
from pymongo import MongoClient

from datetime import datetime, timedelta

# Logging options
import logging

logger_level = "DEBUG"

logger = logging.getLogger(__name__)
logger_set_level = getattr(logging, logger_level)
logger.setLevel(logger_set_level)
formatter = logging.Formatter("%(asctime)s :: %(levelname)s :: %(name)s :: %(message)s")

def select_messages_timeframe(time, messages):
    time = datetime.strptime(time, "%Y-%m-%dT%H:%M:%S%z")
    x = time - timedelta(days=1)
    y = time + timedelta(days=1)
    selection = list(messages.find({'date': { '$gt': x, '$lt': y}}))
    return selection

def vectorize_claim(claim):
    return [0]

def vectorize_messages(messages):
    return [[0]]

def similarity_calculation(vec_1, vec_2):
    return 1

def similar_messages(c_vec, m_vecs, threshold):
    similar_messages = []
    for i, m in enumerate(m_vecs):
        sim = similarity_calculation(c_vec, m)
        if sim > threshold:
            similar_messages.append(i)
    return similar_messages

def main():
    # connect to the mongo db
    logger.info("Connecting to the db")
    vm, host = mongo_utils.access_mongo()
    client = MongoClient(vm, host)

    # get all the images in telegram
    db_telegram = client['telegram_observer']
    collection_messages = db_telegram['messages']

    # look for one claim in the fact-check database
    db_iberifier = client['iberifier']
    collection_maldita = db_iberifier['maldita']
    claim = collection_maldita.find_one({"organization": { "id": 2, "name": 'EFE Verifica' }})
    print(claim)

    # get the messages in the time frame surrounding the claim
    messages_in_frame = select_messages_timeframe(claim['createdAt'], collection_messages)
    print(len(messages_in_frame))
    #for i in messages_in_frame:
    #    print(i)

    # evaluate how close the messages are and assess the threshold of similarity
    c_vec = vectorize_claim(claim)
    m_vecs = vectorize_messages(messages_in_frame)
    threshold = 0.9
    relevant_indices = similar_messages(c_vec, m_vecs, threshold)
    print(len(relevant_indices))


if __name__ == '__main__':
    main()