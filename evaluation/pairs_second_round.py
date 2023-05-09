import json
import random

def main():
    random.seed(1995)

    with open('data_to_evaluate.jsonl') as f:
        previous_evaluation = []
        for line in f:
            previous_evaluation.append(json.loads(line)['_id'].split('_')[0])

    print(previous_evaluation)

    with open('../data/dumps/maldita.json') as f:
        maldita = json.load(f)

    with open('../data/dumps/mynews.json') as f:
        mynews = json.load(f)

    random.shuffle(mynews)
    new_mynews = []
    for n in mynews:
        try:
            if n['keywords_in_title']:
                new_mynews.append(n)
        except KeyError:
            print('no key')
            continue
    new_mynews = [n for n in mynews if n['_id'] not in previous_evaluation]
    news_to_evaluate =  new_mynews[:500]

    news = []
    for n in news_to_evaluate:
        for claim in maldita:
            if n['fact_id'] == claim['_id']:
                n['fact-check'] = claim['text']
                n['claim'] = claim['content']
                news.append(n)


    with open('../data/dumps/tweets.json') as f:
        tweets = json.load(f)

    tweets = [n for n in tweets if n['_id'] not in previous_evaluation]
    tweets_to_evaluate =  tweets[:500]

    tweets = []
    for n in tweets_to_evaluate:
        for claim in maldita:
            if n['fact_id'] == claim['_id']:
                n['claim_id'] = claim['_id']
                n['fact-check'] = claim['text']
                n['claim'] = claim['content']
                tweets.append(n)

    with open('second_round.jsonl', 'w') as o:
        for line in news:
            o.write(json.dumps({'_id':line['_id']['$oid']+'_'+line['fact_id']['$oid'],
                                'text':"***CLAIM***:\n "+line['claim']+
                                       " \n ***FACT-CHECK***: " + line['fact-check'] +
                                       ' \n\n ***TITLE***: \n '+line['Title']+
                                       ' \n ***FIRS LINE OF ARTICLE***: \n '+line['Content'].split('. ')[0]
                                }))
            o.write('\n')

        for line in tweets:
            o.write(json.dumps({'_id':line['_id']['$oid']+'_'+line['claim_id']['$oid'],
                                'text':"***CLAIM***:\n "+line['claim']+
                                        " \n ***FACT-CHECK***: \n "+line['fact-check']+
                                       ' \n\n ***TWEET***: \n '+line['text']
                                }))
            o.write('\n')

if __name__ == "__main__":
    main()
