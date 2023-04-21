import json
import random

def main():
    random.seed(2023)

    # import the maldita claims and select 20
    with open('../data/dumps/maldita.json') as f:
        maldita = json.load(f)

    random.shuffle(maldita)
    claims_to_evaluate = maldita[:20]
    print(claims_to_evaluate[0])
    print(len(claims_to_evaluate))

    # import mynews, filter by the maldita 20 and select 50 of each
    with open('../data/dumps/mynews.json') as f:
        mynews = json.load(f)

    news_to_evaluate =  []
    for claim in claims_to_evaluate:
        news = []
        for n in mynews:
            try: # TODO: this should be changed if all news had the key "keywords_in_title", but some had it to False
                if n['keywords_in_title'] and n['fact_id'] == claim['_id']:
                    n['fact-check'] = claim['text']
                    n['claim'] = claim['content']
                    news.append(n)
            except KeyError:
                continue
        random.shuffle(news)
        news_to_evaluate.extend(news[:50])

    print(len(news_to_evaluate))

    # import tweeter, filter by the maldita 20 and select 100 of each
    with open('../data/dumps/tweets.json') as f:
        collected_tweets = json.load(f)
    #print(collected_tweets[0])
    tweets_to_evaluate =  []
    for claim in claims_to_evaluate:
        tweets = []
        for t in collected_tweets:
            if claim['_id'] in t['fact_id']:
                t['claim_id'] = claim['_id']
                t['fact-check'] = claim['text']
                t['claim'] = claim['content']
                tweets.append(t)
        random.shuffle(tweets)
        tweets_to_evaluate.extend(tweets[:100])

    print(len(tweets_to_evaluate))

    # save the pairs ordered by claim, into a jsonl that has text: ""claim": "","data":" and a clear id
    with open('data_to_evaluate.jsonl', 'w') as o:
        for line in tweets_to_evaluate:
            o.write(json.dumps({'_id':line['_id']['$oid']+'_'+line['claim_id']['$oid'],
                                'text':"***CLAIM***:\n "+line['claim']+
                                        " \n ***FACT-CHECK***: \n "+line['fact-check']+
                                       ' \n\n ***TWEET***: \n '+line['text']
                                }))
            o.write('\n')

        for line in news_to_evaluate:
            o.write(json.dumps({'_id':line['_id']['$oid']+'_'+line['fact_id']['$oid'],
                                'text':"***CLAIM***:\n "+line['claim']+
                                       " \n ***FACT-CHECK***: " + line['fact-check'] +
                                       ' \n\n ***TITLE***: \n '+line['Title']+
                                       ' \n ***FIRS LINE OF ARTICLE***: \n '+line['Content'].split('. ')[0]
                                }))
            o.write('\n')

if __name__ == "__main__":
    main()