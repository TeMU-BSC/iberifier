
import json
from sklearn.metrics import confusion_matrix, accuracy_score
import seaborn as sns
from sentence_transformers import SentenceTransformer, util
from transformers import pipeline, AutoTokenizer
import sys

def prepare(sentence_pairs, tokenizer):
    sentence_pairs_prep = []
    for s1, s2 in sentence_pairs:
        sentence_pairs_prep.append(f"{tokenizer.cls_token} {s1}{tokenizer.sep_token}{tokenizer.sep_token} {s2}{tokenizer.sep_token}")
    return sentence_pairs_prep

def main():
    source = 'tweets'
    model_source = sys.argv[1]

    with open('../data/eval_'+source+'.jsonl') as f:
        data = []
        for line in f:
            data.append(json.loads(line))


    print(model_source, source)
    if model_source == 'distiluse_multi':  # why these models? https://www.sbert.net/docs/pretrained_models.html#multi-lingual-models
        model = SentenceTransformer('sentence-transformers/distiluse-base-multilingual-cased-v1')
    elif model_source == 'paraph':
        model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-mpnet-base-v2')
    elif model_source == 'spanish':
        model = SentenceTransformer('hiiamsid/sentence_similarity_spanish_es')
    elif model_source == 'supervised_sts':
        path_sts = '../../models/roberta-base-bne-sts'
        tokenizer_sts = AutoTokenizer.from_pretrained(path_sts)
        model = pipeline('text-classification', model=path_sts, tokenizer=tokenizer_sts, truncation=True)
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
            if model_source != 'supervised_sts':
                for line in data:
                    if label == line['label_eng']:
                        # compare the claim to the text
                        c_embeddings = model.encode([line['claim'], line['text']], convert_to_tensor=True)
                        claim_sim = util.cos_sim(c_embeddings[0], c_embeddings[1])

                        # compare the fact-check to the text
                        f_embeddings = model.encode([line['fact-check'], line['text']], convert_to_tensor=True)
                        factcheck_sim = util.cos_sim(f_embeddings[0], f_embeddings[1])

                        all_results.append({'true_label': label,'claim_similarity':claim_sim,'factcheck_similarity':factcheck_sim})
            else:
                for line in data:
                    if label == line['label_eng']:
                        # compare the claim to the text
                        c_predictions = model(prepare([(line['claim'], line['text'])], tokenizer_sts), add_special_tokens=False)
                        claim_sim = c_predictions[0]['score']

                        # compare the fact-check to the text
                        c_predictions = model(prepare([(line['fact-check'], line['text'])], tokenizer_sts),
                                              add_special_tokens=False)
                        factcheck_sim = c_predictions[0]['score']

                        all_results.append(
                            {'true_label': label, 'claim_similarity': claim_sim, 'factcheck_similarity': factcheck_sim})

    for line in all_results:
        if line['claim_similarity'] >= line['factcheck_similarity']:
            line['result'] = 'The text disseminates the false claim'
        elif line['claim_similarity'] < line['factcheck_similarity']:
            line['result'] = 'The text is about the claim, but it does not support it'


    print(accuracy_score([line['true_label'] for line in all_results], [line['result'] for line in all_results]))
    cf_matrix = confusion_matrix([line['true_label'] for line in all_results], [line['result'] for line in all_results], labels=list(mapping_labels.keys())[:2])
    print(cf_matrix)
    pal = sns.light_palette("seagreen", as_cmap=True)
    sns_plot = sns.heatmap(cf_matrix, xticklabels=[1,2], yticklabels=[1,2], cmap=pal, annot=True, fmt=',d')
    fig = sns_plot.get_figure()
    fig.savefig("relevant_plots/te_heatmap_twoways_sts_"+model_source+".png")





if __name__ == "__main__":
    main()