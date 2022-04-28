from twitter_search import TweetSearchUtil
from pymongo import MongoClient

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

    # get only the documents who were not searched for
    itercol = keywords_col.find({'last_date':{'$exists':False}})
    for doc in itercol:
        query = ' '.join(doc['keyword']) + ' -is:retweet'
        
        # Ensure the query is less than 1024 characters as imposed by Twitter
        i=1
        while len(query) > 1024:
            query = ' '.join(doc['keyword'][:-i]) + ' -is:retweet'
            i +=1
        
        tweets = search_twitter(query)
        insert_tweets_mongo(tweets, doc['_id'])
        

if __name__ == '__main__':
    main()