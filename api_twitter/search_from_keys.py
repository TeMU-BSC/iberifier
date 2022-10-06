import logging
import os
import sys
from datetime import datetime

import yaml

from api_twitter import search_twitter
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from mongo_utils import mongo_utils



logger = logging.getLogger(__name__)

# Load config and credentials

config_all = yaml.safe_load(open("../config_files/config.yaml"))

mongo_cred_path = os.path.join(
    os.path.dirname(__file__),
    "../config_files",
    config_all["mongodb_params"]["mongodb_cred_filename"],
)
mongodb_credentials = yaml.safe_load(open(mongo_cred_path))[
    "mongodb_credentials"]

twitter_cred_path = os.path.join(
    os.path.dirname(__file__),
    "../config_files",
    config_all["api_twitter_params"]["twitter_cred_filename"],
)
twitter_credentials = yaml.safe_load(open(twitter_cred_path))[
    "search_tweets_api"]


def insert_tweets_mongo(tweet, collection):

    collection.update_one({"id": tweet["id"]}, {"$set": tweet}, upsert=True)


def main():
    # Iterate through collection
    mydb = mongo_utils.get_mongo_db()
    cols_factcheckers = ['maldita', 'google']
    col_tweets = config_all['mongodb_params']['col_tweets']

    keyword_pairs_key = config_all['keywords_params']['keywords_pair_keys']

    max_claims_per_day = config_all['api_twitter_params']['max_claims_per_day']
    twitter_search_params = config_all['api_twitter_params']['search_params']
    twitter_rule_params = config_all['api_twitter_params']['rule_params']
    twitter_additional_query = twitter_search_params['additional_query']
    twitter_additional_query = ' '.join(twitter_additional_query)

    sources_to_update = []

    # get only the documents who were not searched for
    for col in cols_factcheckers:
        itercol = mydb[col].find(
            {"searched_on": {"$exists": False},
             keyword_pairs_key: {"$ne": None}}
        ).limit(max_claims_per_day)

        for doc in itercol:
            news_id = doc["_id"]
            print(news_id)
            post_date_str = doc["createdAt"]
            post_date = datetime.strptime(post_date_str, "%Y-%m-%dT%H:%M:%S%z")
            twitter_search_params['date'] = post_date
            keyword_pairs = doc[keyword_pairs_key]

            i = 0
            while i < len(keyword_pairs):

                query = " ".join(keyword_pairs[i])
                newquery = query
                i += 1
                # Add bigrams to query until it reaches the 1024 query limit
                # or all bigrams are added
                # TODO include a different strategy otherwise the keywords will be the first one only
                # TODO or include that in the keywords_processor script
                while i < len(keyword_pairs) and len(newquery) < 1024 - (
                    len("() {}".format(twitter_additional_query))
                ):
                    query = newquery
                    newquery += " OR " + " ".join(doc[keyword_pairs][i])
                    i += 1

                # query = "(" + query + ") -is:retweet"

                # tweets = search_twitter(query, post_date)
                # insert_tweets_mongo(tweets, news_id)

                tweets = search_twitter(
                    twitter_credentials, query, search_params=twitter_search_params, rule_params=twitter_rule_params)

                for tweet in tweets:
                    insert_tweets_mongo(tweet, col_tweets)

            sources_to_update.append(news_id)

        mydb[col].update_many(
            {"_id": {"$in": sources_to_update}}, {
                "$set": {"searched_on": datetime.now()}}
        )


if __name__ == "__main__":
    main()
