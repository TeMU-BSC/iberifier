
import json
import sys
from sentence_transformers import SentenceTransformer, util
import numpy as np
import matplotlib.pyplot as plt
from transformers import pipeline, AutoTokenizer
from sklearn.metrics import accuracy_score, classification_report

def prepare(sentence_pairs, tokenizer):
    sentence_pairs_prep = []
    for s1, s2 in sentence_pairs:
        sentence_pairs_prep.append(f"{tokenizer.cls_token} {s1}{tokenizer.sep_token}{tokenizer.sep_token} {s2}{tokenizer.sep_token}")
    return sentence_pairs_prep

def choose_thresholds(upper_boundary, lower_boundary, trials):
    thresholds = [lower_boundary, upper_boundary]
    if upper_boundary >= lower_boundary:
        bit = (upper_boundary-lower_boundary)/trials
        threshold_attempt = lower_boundary
        for i in range(trials-1):
            threshold_attempt += bit
            thresholds.append(threshold_attempt)
    return thresholds

def calculate_accuracy(threshold, values, labels, report=False):
    predicted_labels = []
    for v in values:
        if v > threshold:
            predicted_labels.append(1)
        elif v <= threshold:
            predicted_labels.append(0)
    if report:
        print(classification_report(labels, predicted_labels))
    return accuracy_score(labels, predicted_labels)

def maximize_accuracy(values, labels, trials=5):
    negative_values = []
    positive_values = []
    for i, line in enumerate(labels):
        if line == 0:
            negative_values.append(values[i])
        elif line == 1:
            positive_values.append(values[i])
    upper_boundary = np.mean(positive_values)
    lower_boundary = np.mean(negative_values)
    thresholds = choose_thresholds(upper_boundary, lower_boundary, trials)
    best_accuracy = 0
    best_threshold = 0
    for t in thresholds:
        accuracy = calculate_accuracy(t, values, labels)
        if accuracy > best_accuracy:
            best_threshold = t
            best_accuracy = accuracy
    calculate_accuracy(best_threshold, values, labels, report = True)
    return best_threshold, best_accuracy

def main():
    source = sys.argv[1] # news tweets
    model_source = sys.argv[2]
    plot = True
    relevant = True

    with open('../data/eval_'+source+'.jsonl') as f:
        data = []
        for line in f:
            data.append(json.loads(line))

    ordinal_labels = {'The text disseminates the false claim':0,
                 'The text is about the claim, but it does not support it':0.25,
                 'The text is on topic but not about this precise claim':0.50,
                 'The text is on another topic':0.75,
                 'The text is not readable':1}

    mapping_labels = {'The text disseminates the false claim': 1,
                      'The text is about the claim, but it does not support it': 1,
                      'The text is on topic but not about this precise claim': 1, # change to 0
                      'The text is on another topic': 0,
                      'The text is not readable': 0}
    if relevant:
        mapping_labels['The text is on topic but not about this precise claim'] = 0

    print(model_source, source)
    if model_source == 'distiluse_multi': # why these models? https://www.sbert.net/docs/pretrained_models.html#multi-lingual-models
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

    all_sts_values = []
    all_label_values = []
    all_ordinal = []
    appended_all_sts_values = []
    for label, value in mapping_labels.items():
        sts_values = []
        label_values = []
        ordinal = []
        if model_source != 'supervised_sts':
            for line in data:
                if label == line['label_eng']:
                    embeddings = model.encode([line['claim'], line['text']], convert_to_tensor=True)
                    sim = util.cos_sim(embeddings[0], embeddings[1])
                    sts_values.append(float(sim))
                    #sts_values.append(1)
                    label_values.append(mapping_labels[line['label_eng']])
                    ordinal.append(ordinal_labels[line['label_eng']])
        else:
            sentences = []
            for line in data:
                if label == line['label_eng']:
                    sentences.append((line['claim'], line['text']))
                    label_values.append(mapping_labels[line['label_eng']])
                    ordinal.append(ordinal_labels[line['label_eng']])
            predictions = model(prepare(sentences, tokenizer_sts), add_special_tokens=False)
            sts_values = [p['score'] for p in predictions]
            #sts_values = [1 for i in range(len(sentences))]


        print(label, np.mean(sts_values), len(sts_values))
        all_sts_values.extend(sts_values)
        all_label_values.extend(label_values)
        all_ordinal.extend(ordinal)
        if plot:
            appended_all_sts_values.append(sts_values)

    print(np.corrcoef(all_sts_values, all_ordinal))
    threshold, accuracy = maximize_accuracy(all_sts_values, all_label_values)
    print(threshold, accuracy)

    if plot:
        f = plt.figure()
        f.set_figwidth(9)
        plt.rc('xtick', labelsize=6)
        violin_plot = plt.violinplot(appended_all_sts_values[::-1], vert = False, showmedians=True)
        if source == 'news':
            plt.xlabel('Similarity between Claim and Title')
        else:
            plt.xlabel('Similarity between Claim and Tweet')

        plt.yticks([1,2,3,4,5],
                   list(mapping_labels.keys())[::-1])
        for i, pc in enumerate(violin_plot["bodies"], 1):
            if relevant:
                index_limit = 3
            else:
                index_limit = 2
            if i <= index_limit: # change to 3
                pc.set_facecolor('#101E4A')
            else:
                pc.set_facecolor('#FFDD4A')
            pc.set_alpha(0.8)
            pc.set_edgecolor('grey')

        plt.vlines(x=threshold, ymin=0, ymax=5.5, colors='grey')
        plt.annotate('Accuracy '+str(accuracy), (0, 0), (140, 5),
                     fontsize=10, xycoords='figure fraction', textcoords='offset points')
        if relevant:
            out_path = 'relevant_plots/'
        else:
            out_path = 'ontopic_plots/'

        plt.savefig(out_path+source+'_'+model_source+".png", bbox_inches='tight', pad_inches = 0.05)





if __name__ == "__main__":
    main()