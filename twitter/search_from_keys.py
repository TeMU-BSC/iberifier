from twitter_search import TweetSearchUtil
from pymongo import MongoClient
import datetime

def search_twitter(query):
    tsu = TweetSearchUtil('../twittercredentials.yaml')
    tweets = tsu.search_tweets_by_query(query, results_total=100, results_per_call=100, # for testing purpose limited to 100
                                tweet_fields='author_id,conversation_id,created_at,geo,id,lang,public_metrics,text')
    return tweets

def insert_tweets_mongo(tweets, source):
    myclient = MongoClient('mongodb://127.0.0.1:27017/iberifier')
    mydb = myclient.get_default_database()
    tweets_col = mydb['twitter_test']

    for t in tweets:
        # Set the twitter id as the mongo id
        t['_id'] = t['id']
        t['source'] = source

    tweets_col.insert_many(tweets)

def main():
    # Iterate through collection
    myclient = MongoClient('mongodb://127.0.0.1:27017/iberifier')
    mydb = myclient.get_default_database()
    keywords_col = mydb["keywords_twitter"]

    sources_to_update = []
    # get only the documents who were not searched for
    itercol = keywords_col.find({'searched_on':{'$exists':False}})
    for doc in itercol:
        news_id = doc['_id']
        for key_list in doc['bigrams']:
            
            query = ' '.join(key_list) + ' -is:retweet'
            
            # Ensure the query is less than 1024 characters as imposed by Twitter
            i=1
            while len(query) > 1024:
                query = ' '.join(key_list[:-i]) + ' -is:retweet'
                i +=1
            
            tweets = search_twitter(query)
            insert_tweets_mongo(tweets, news_id)

        sources_to_update.append(news_id)

    keywords_col.update_many(
        {'_id':{'$in':sources_to_update}},
        {"$set": { "searched_on" : datetime.datetime.now() }}
    )
        

if __name__ == '__main__':
    main()