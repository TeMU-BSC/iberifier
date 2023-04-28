
import json
from sklearn.metrics import confusion_matrix
import seaborn as sns
from sentence_transformers import SentenceTransformer, util

def main():
    source = 'tweets'
    model_source =  'distiluse_multi'

    with open('../data/eval_'+source+'.jsonl') as f:
        data = []
        for line in f:
            data.append(json.loads(line))


    print(model_source, source)
    if model_source == 'distiluse_multi':  # why these models? https://www.sbert.net/docs/pretrained_models.html#multi-lingual-models
        model = SentenceTransformer('sentence-transformers/distiluse-base-multilingual-cased-v1')
    else:
        print('There is no such model.')
        exit()

    mapping_labels = {'The text disseminates the false claim': 1,
                      'The text is about the claim, but it does not support it': 1,
                      'The text is on topic but not about this precise claim': 0,
                      'The text is on another topic': 0,
                      'The text is not readable': 0}

    all_results = []
    for label, value in mapping_labels.items():
        if value != 0:
            for line in data:
                if label == line['label_eng']:
                    # compare the claim to the text
                    c_embeddings = model.encode([line['claim'], line['text']], convert_to_tensor=True)
                    claim_sim = util.cos_sim(c_embeddings[0], c_embeddings[1])

                    # compare the fact-check to the text
                    f_embeddings = model.encode([line['fact-check'], line['text']], convert_to_tensor=True)
                    factcheck_sim = util.cos_sim(f_embeddings[0], f_embeddings[1])

                    all_results.append({'true_label': label,'claim_similarity':claim_sim,'factcheck_similarity':factcheck_sim})

    for line in all_results:
        if line['claim_similarity'] >= line['factcheck_similarity']:
            line['result'] = 'The text disseminates the false claim'
        elif line['claim_similarity'] < line['factcheck_similarity']:
            line['result'] = 'The text is about the claim, but it does not support it'


    cf_matrix = confusion_matrix([line['true_label'] for line in all_results], [line['result'] for line in all_results], labels=list(mapping_labels.keys())[:2])
    print(cf_matrix)
    sns_plot = sns.heatmap(cf_matrix, xticklabels=list(mapping_labels.keys())[:2], yticklabels=list(mapping_labels.keys())[:2])
    fig = sns_plot.get_figure()
    fig.savefig("plots/te_heatmap_twoways_sts.png")





if __name__ == "__main__":
    main()