import logging
import os
import json
import sys
import logging.config
import datetime
from bson import ObjectId
from bson.json_util import dumps

import yaml

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from mongo_utils import mongo_utils

logger = logging.getLogger(__name__)

# Load config and credentials

config_path = os.path.join(os.path.dirname(
    __file__), '../config', 'config.yaml')
config_all = yaml.safe_load(open(config_path))


# TODO: Absolutely inefficient, need to use an aggregate, project and foreign key instead of that
def get_list_fact_ids(date1, date2, mydb, col_maldita):
    for fact_id in mydb[col_maldita].find({ "date": {"$gte": date1, "$lte": date2}, "organization.name": { "$in": ['Maldita.es', 'EFE Verifica', 'Newtral']}}, {'fact_id'}):
        yield fact_id


def main():
    # Iterate through collection
    mydb = mongo_utils.get_mongo_db()
    col_tweets = config_all['mongodb_params']['tweets']['name']
    col_mynews = config_all['mongodb_params']['mynews']['name']
    col_maldita = config_all['mongodb_params']['maldita']['name']
    col_google = config_all['mongodb_params']['google']['name']
    col_keywords = config_all['mongodb_params']['keywords']['name']

    # Set the date range for keywords search
    date1 = datetime.datetime(2023, 2, 1)
    date2 = datetime.datetime(2023, 4, 1)

    relevant_fact_per_date = list(get_list_fact_ids(
        date1, date2, mydb, col_maldita))

    # Retrieve the list of relevant maldita documents
    relevant_maldita = mydb[col_maldita].find({
        "_id": {"$in": [k['_id'] for k in relevant_fact_per_date]}
    })

    # Retrieve the list of relevant tweets documents
    relevant_tweets = mydb[col_tweets].find({
        "fact_id": {"$in": [k['_id'] for k in relevant_fact_per_date]}
    })

    # Retrieve the list of relevant mynews documents
    relevant_mynews = mydb[col_mynews].find({
        "fact_id": {"$in": [k['_id'] for k in relevant_fact_per_date]}
    })

    # Retrieve the list of keywords documents
    relevant_keywords_doc = mydb[col_mynews].find({
        "fact_id": {"$in": [k['_id'] for k in relevant_fact_per_date]}
    })

    # Dump the relevant documents to JSON files
    with open("keywords.json", "w") as f:
        f.write(dumps(relevant_keywords_doc))
    with open("maldita.json", "w") as f:
        f.write(dumps(relevant_maldita))
    with open("tweets.json", "w") as f:
        f.write(dumps(relevant_tweets))
    with open("mynews.json", "w") as f:
        f.write(dumps(relevant_mynews))


if __name__ == "__main__":
    main()
