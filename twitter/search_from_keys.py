from .twitter_search import TweetSearchUtil
from datetime import datetime
from datetime import timedelta

import sys,os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from mongo_utils import mongo_utils

# for testing purpose limited these are limited now
MAX_TWEETS_RETRIEVED = 500
MAX_CLAIMS_PER_DAY = 1

def search_twitter(query, date=None):
    tsu = TweetSearchUtil('twittercredentials.yaml')
    if date == None:
        tweets = tsu.search_tweets_by_query(query, results_total=MAX_TWEETS_RETRIEVED,
                                tweet_fields='author_id,conversation_id,created_at,geo,id,lang,public_metrics,text')
    else:
        start_date = date + timedelta(days=-30)
        end_date = date + timedelta(days=30)
        tweets = tsu.search_tweets_by_query(query, results_total=MAX_TWEETS_RETRIEVED,
                                tweet_fields='author_id,conversation_id,created_at,geo,id,lang,public_metrics,text',
                                start_time=start_date.strftime("%Y-%m-%d %H:%M"),
                                end_time=end_date.strftime("%Y-%m-%d %H:%M")
                                )

    return tweets

def insert_tweets_mongo(tweets, source):
    mydb = mongo_utils.get_mongo_db()
    tweets_col = mydb['twitter_test']

    for t in tweets:
        # Set the twitter id as the mongo id
        t['_id'] = t['id']
        t['source'] = source
    print(len(tweets))
    tweets_col.insert_many(tweets)


def main():
    # Iterate through collection
    mydb = mongo_utils.get_mongo_db()
    keywords_col = mydb["maldita"]

    sources_to_update = []
    # get only the documents who were not searched for
    itercol = keywords_col.find(
        {'searched_on':{'$exists':False},
        'bigrams':{'$ne':None}}
        ).limit(MAX_CLAIMS_PER_DAY)

    for doc in itercol:
        news_id = doc['_id']
        print(news_id)
        post_date_str = doc['createdAt']
        post_date = datetime.strptime(
            post_date_str,
            '%Y-%m-%dT%H:%M:%S%z'
            )
        
        i = 0
        while i < len(doc['bigrams']):
            
            query = ' '.join(doc['bigrams'][i])
            newquery = query
            # Add bigrams to query until it reaches the 1024 query limit
            # or all bigrams are added
            while i < len(doc['bigrams']) and len(newquery) < (1024 - len(' -is:retweet')):
                i+=1
                query = newquery
                newquery += ' OR '+' '.join(doc['bigrams'][i])
            
            query += ' -is:retweet'

            tweets = search_twitter(query, post_date)
            insert_tweets_mongo(tweets, news_id)

        sources_to_update.append(news_id)

    keywords_col.update_many(
        {'_id':{'$in':sources_to_update}},
        {"$set": { "searched_on" : datetime.datetime.now() }}
    )
        

if __name__ == '__main__':
    main()
