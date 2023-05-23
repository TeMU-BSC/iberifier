import json
import sys

def main():
    translate = {'Difunde la claim falsa': 'The text disseminates the false claim',
                'Es sobre la claim pero no la apoya': 'The text is about the claim, but it does not support it',
                'Es sobre el tema pero no sobre la misma claim': 'The text is on topic but not about this precise claim',
                'Es otro tema': 'The text is on another topic',
                'Tweet ilegible': 'The text is not readable'}

    with open(sys.argv[1]) as f:
        data = []
        for line in f:
            data.append(json.loads(line))

    with open('../data/eval_'+sys.argv[1], 'w') as o:
        for line in data:
            claim = line['text'][14:]
            claim, rest = claim.split("\n ***FACT-CHECK***: ")
            try:
                fact_check, text = rest.split(' \n\n ***TWEET***: \n ')
            except ValueError:
                fact_check, rest = rest.split(' \n\n ***TITLE***: \n ')
                text, content = rest.split(' \n ***FIRS LINE OF ARTICLE***: \n ')

            id_tweet, id_claim = line['_id'].split('_')
            #print(claim, fact_check, tweet, id_tweet, id_claim)
            o.write(json.dumps({'id_tweet':id_tweet, 'id_claim':id_claim, 'claim':claim,
                                'fact-check':fact_check, 'text':text, 'label': line['accept'][0], 'label_eng':translate[line['accept'][0]]}))
            o.write('\n')




if __name__ == "__main__":
    main()