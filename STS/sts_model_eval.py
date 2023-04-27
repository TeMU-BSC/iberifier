
import json
import sys
from sentence_transformers import SentenceTransformer, util
#from scipy import spatial
import numpy as np
import matplotlib.pyplot as plt
from transformers import pipeline, AutoTokenizer
from sklearn.metrics import balanced_accuracy_score

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

def calculate_accuracy(threshold, values, labels):
    predicted_labels = []
    for v in values:
        if v > threshold:
            predicted_labels.append(1)
        elif v <= threshold:
            predicted_labels.append(0)
    return balanced_accuracy_score(labels, predicted_labels)

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
    return best_threshold, best_accuracy

def main():
    source = sys.argv[1] # news tweets
    model_source = sys.argv[2]
    inform = True
    plot = True

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
                      'The text is on topic but not about this precise claim': 1,
                      'The text is on another topic': 0,
                      'The text is not readable': 0}

    print(model_source, source)
    if model_source == 'xlm_multi':
        model = SentenceTransformer('sentence-transformers/stsb-xlm-r-multilingual')
    elif model_source == 'distiluse_multi':
        model = SentenceTransformer('sentence-transformers/distiluse-base-multilingual-cased')
    elif model_source == 'spanish':
        model = SentenceTransformer('hiiamsid/sentence_similarity_spanish_es')
    elif model_source == 'supervised_sts':
        path_sts = '../../models/roberta-base-bne-sts'
        tokenizer_sts = AutoTokenizer.from_pretrained(path_sts)
        model = pipeline('text-classification', model=path_sts, tokenizer=tokenizer_sts, truncation=True)
        # model_te = pipeline("text-classification", model="PlanTL-GOB-ES/roberta-large-bne-te")
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
                    #embeddings = model.encode([line['claim'], line['text']])
                    #dist = spatial.distance.cosine(embeddings[0], embeddings[1])
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
        if inform:
            all_sts_values.extend(sts_values)
            all_label_values.extend(label_values)
            all_ordinal.extend(ordinal)
        if plot:
            appended_all_sts_values.append(sts_values)

    if inform:
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
            if i <= 2:
                pc.set_facecolor('#101E4A')
            else:
                pc.set_facecolor('#FFDD4A')
            pc.set_alpha(0.8)
            pc.set_edgecolor('grey')

        plt.savefig(source+'_'+model_source+".png", bbox_inches='tight', pad_inches = 0.05)





if __name__ == "__main__":
    main()