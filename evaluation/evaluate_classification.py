import json
from collections import Counter
import sys
from sklearn.metrics import confusion_matrix, accuracy_score, classification_report

def evaluate(data, source_content, category, mapping):
    content_dict = {}
    for content in source_content:
        try:
            content_dict[content['_id']['$oid']] = content[category]
        except KeyError as e:
            if e.args[0] == 'claim_finer_relation':
                pass
            else:
                print('An instance is missing the classification')
                exit()
    source_ids = [line['_id']['$oid'] for line in source_content]

    gold_labels = []
    predicted_labels = []
    for line in data:
        #print(line)
        _id = line['_id'].split('_')[0]
        if _id in source_ids and mapping[line['accept'][0]] != None:
            try:
                predicted_labels.append(content_dict[_id]) # TODO: in the finer classification, some instances won't have the label, consider what to do with them
                gold_labels.append(mapping[line['accept'][0]])
            except KeyError:
                pass

    print(len(predicted_labels), len(gold_labels))
    print(classification_report(gold_labels, predicted_labels))
    print(accuracy_score(gold_labels, predicted_labels))
    print(confusion_matrix(gold_labels, predicted_labels))

def main():
    with open(sys.argv[1]) as f:
        data = []
        for line in f:
            data.append(json.loads(line))

    topic_gold_to_predicted_mapping = {'Difunde la claim falsa':'on-topic',
                                 'Es sobre la claim pero no la apoya':'on-topic',
                                 'Es sobre el tema pero no sobre la misma claim':'on-topic',
                                 'Es otro tema':'off-topic',
                                 'Tweet ilegible':'off-topic'}

    claim_gold_to_predicted_mapping = {'Difunde la claim falsa': 'on-claim',
                                 'Es sobre la claim pero no la apoya': 'on-claim',
                                 'Es sobre el tema pero no sobre la misma claim': 'off-claim',
                                 'Es otro tema': 'off-claim',
                                 'Tweet ilegible': 'off-claim'}

    claim_finer_gold_to_predicted_mapping = {'Difunde la claim falsa': 'disseminates',
                                 'Es sobre la claim pero no la apoya': 'not-disseminates',
                                 'Es sobre el tema pero no sobre la misma claim': None,
                                 'Es otro tema': None,
                                 'Tweet ilegible': None}


    sources = ['mynews', 'tweets']
    for source in sources:
        with open('../data/dumps/'+source+'.json') as f:
            source_content = json.load(f)

        #evaluate(data, source_content, 'topic_relation', topic_gold_to_predicted_mapping)

        if source == 'tweets':
            evaluate(data, source_content, 'claim_relation', claim_gold_to_predicted_mapping)
            evaluate(data, source_content, 'claim_finer_relation', claim_finer_gold_to_predicted_mapping)


if __name__ == "__main__":
    main()


