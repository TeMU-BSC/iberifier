import sys
import os
import argparse

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
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
    # time = datetime.strptime(time, "%Y-%m-%dT%H:%M:%S%z")
    x = time - timedelta(days=timeframe)
    y = time + timedelta(days=timeframe)
    selection = list(messages.find({source["date"]: {"$gt": x, "$lt": y}})) # also filter by related to
    return selection


def mbert_vectorizer(text, model):
    # Compute embedding for both lists
    vector = model.encode(text, convert_to_tensor=True)
    return vector


def vectorize_claim(claim, model):
    text = claim["text"]
    vector = mbert_vectorizer(text, model)
    return vector


def vectorize_messages(messages, model, source):
    vectors = []
    for m in messages:
        vector = mbert_vectorizer(m[source["text"]], model)
        vectors.append(vector)
    return vectors


def similarity_calculation(vec_1, vec_2):
    sim = util.pytorch_cos_sim(vec_1, vec_2)
    # print(sim)
    return sim


def similar_messages(c_vec, m_vecs, threshold):
    similar_messages = []
    for i, m in enumerate(m_vecs):
        sim = similarity_calculation(c_vec, m)
        if sim > threshold:
            similar_messages.append(i)
    return similar_messages


# TODO: in some cases we might also be interested in the body
def get_source_keys(source):
    """Defines the right fields for each source"""
    source_keys = {}
    if source == "telegram":
        source_keys["date"] = "date"
        source_keys["text"] = "message"
    elif source == "tweets":
        source_keys["date"] = "date"
        source_keys["text"] = "text"
    elif source == "lusa":
        source_keys["date"] = "date"
        source_keys["text"] = "headline"
    elif source == "mynews":
        source_keys["date"] = "date"
        source_keys["text"] = "Title"
    return source_keys

def get_messages(db, claim, args):
    if args.source == "telegram":
        db_telegram = mongo_utils.get_mongo_db("telegram_observer")
        collection_messages = db_telegram["messages"]
        source_keys = get_source_keys(args.source)
    else:
        collection_messages = db[args.source]
        if len(list(collection_messages.find())) == 0:
            print(
                "This data does not exist, we currently have the collections:", db.list_collection_names()
            )
            return
        else:
            source_keys = get_source_keys(args.source)

    messages_in_frame = select_messages_timeframe(
        claim["date"], collection_messages, args.timeframe, source_keys
    )
    print(len(messages_in_frame))
    return messages_in_frame, source_keys

def main():
    parser = argparse.ArgumentParser()
    parser = get_arguments(parser)
    args = parser.parse_args()
    print(args)

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
        claim = collection.find_one(
            {"date": {"$gt": datetime(2021, 11, 1), "$lt": datetime(2021, 11, 30)}} # not implemented yet
        )
    else:
        claim = collection.find_one()
    print(claim)

    # get all the messages from the source
    messages_in_frame, source_keys = get_messages(db_iberifier, claim, args)
    #for i in messages_in_frame:
    #   print(i)
    #exit()
    # evaluate how close the messages are and assess the threshold of similarity
    model = SentenceTransformer("AIDA-UPM/mstsb-paraphrase-multilingual-mpnet-base-v2")
    c_vec = vectorize_claim(claim, model)
    m_vecs = vectorize_messages(messages_in_frame, model, source_keys)
    threshold = args.threshold
    print(threshold)
    relevant_indices = similar_messages(c_vec, m_vecs, threshold)
    print(len(relevant_indices))

    for i, m in enumerate(messages_in_frame):
        if i in relevant_indices:
            print(m[source_keys["text"]], m["_id"])


if __name__ == "__main__":
    main()
