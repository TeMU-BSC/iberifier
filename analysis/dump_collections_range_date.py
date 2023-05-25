from __future__ import with_statement
import logging
import os
import sys
import logging.config
import datetime
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
def get_list_fact_ids(date1, date2, mydb, col_maldita, all_records=False):
    if all_records is False:
        find_query = {"date": {"$gte": date1, "$lte": date2},
                      # "organization.name": {"$in": ['Maldita.es', 'EFE Verifica', 'Newtral']},
                      # "organizationCalification.calification.name": 'Falso'
                      }
    if all_records is True:
        find_query = {"date": {"$gte": date1, "$lte": date2}}

    for fact_id in mydb[col_maldita].find(find_query, {'fact_id'}):
        yield fact_id

def main():
    # Iterate through collection
    mydb = mongo_utils.get_mongo_db()
    col_tweets = config_all['mongodb_params']['tweets']['name']
    col_mynews = config_all['mongodb_params']['mynews']['name']
    col_maldita = config_all['mongodb_params']['maldita']['name']
    col_keywords = config_all['mongodb_params']['keywords']['name']
    file_dump_tweets = config_all['analysis']['dump_tweets_file']
    file_dump_mynews = config_all['analysis']['dump_mynews_file']
    file_dump_maldita = config_all['analysis']['dump_maldita_file']
    file_dump_keywords = config_all['analysis']['dump_keywords_file']

    # Set the date range for keywords search
    from_date_dump = datetime.datetime(2023, 3, 8)
    until_date_dump = datetime.datetime(2023, 4, 8)

    relevant_fact_per_date = list(get_list_fact_ids(
        from_date_dump, until_date_dump, mydb, col_maldita, all_records=False))

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
        "fact_id": {"$in": [k['_id'] for k in relevant_fact_per_date]},
        'keywords_in_title': True
    })

    # Retrieve the list of keywords documents
    relevant_keywords_doc = mydb[col_keywords].find({
        "fact_id": {"$in": [k['_id'] for k in relevant_fact_per_date]}
    })

    # Dump the relevant documents to JSON files
    with open(file_dump_keywords, "w") as f:
        f.write(dumps(relevant_keywords_doc))
    with open(file_dump_maldita, "w") as f:
        f.write(dumps(relevant_maldita))
    with open(file_dump_tweets, "w") as f:
        f.write(dumps(relevant_tweets))
    with open(file_dump_mynews, "w") as f:
        f.write(dumps(relevant_mynews))


print ( 0 )

if __name__ == "__main__":
    main()
