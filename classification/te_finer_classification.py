
import json
import random
import sys
from transformers import pipeline
from sklearn.metrics import accuracy_score, confusion_matrix, classification_report
import seaborn as sns

def main():
    source = sys.argv[1] # news tweets
    model_source =  sys.argv[2]

    with open('../data/eval_'+source+'.jsonl') as f:
        data = []
        for line in f:
            data.append(json.loads(line))


    print(model_source, source)
    if model_source == 'recognai':
        model = pipeline("text-classification", model="Recognai/bert-base-spanish-wwm-cased-xnli", truncation=True)
        te_labels = ['entailment', 'contradiction', 'neutral']
    elif model_source == 'roberta':
        model = pipeline("text-classification", model="PlanTL-GOB-ES/roberta-large-bne-te", truncation=True)
        te_labels = ['entailment', 'contradiction', 'not_entailment']
    elif model_source == 'xlm':
        model = pipeline("text-classification", model="tuni/xlm-roberta-large-xnli-finetuned-mnli", truncation=True)
        te_labels = ['entailment', 'contradiction', 'neutral']
    else:
        print('There is no such model.')
        exit()

    mapping_labels = {'The text disseminates the false claim': te_labels[0],
                      'The text is about the claim, but it does not support it': te_labels[1],
                      'The text is on topic but not about this precise claim': te_labels[2],
                      'The text is on another topic': 0,
                      'The text is not readable': 0}

    all_p_labels = []
    all_labels = []
    #all_values = []
    for label, value in mapping_labels.items():
        if value != 0:
            sentences = []
            for line in data:
                if label == line['label_eng']:
                    sentences.append(line['claim']+' '+line['text'])
                    all_labels.append(mapping_labels[label])
                    #all_values.append(value)
            predictions = model(sentences)
            p_labels = [line['label'] for line in predictions]
            #p_labels = [1 for i in range(len(sentences))]
            all_p_labels.extend(p_labels)

    print(set(all_p_labels), len(all_p_labels))
    print(set(all_labels), len(all_labels))
    print(classification_report(all_labels, all_p_labels))
    print(accuracy_score(all_labels, all_p_labels))
    cf_matrix = confusion_matrix(all_labels, all_p_labels, labels=te_labels)
    print(cf_matrix)
    pal = sns.color_palette("light:#1b1c3a", as_cmap=True)
    sns_plot = sns.heatmap(cf_matrix, xticklabels=[1,2,3], yticklabels=te_labels, cmap=pal, annot=True, fmt=',d')
    te_labels_short = ['entailment', 'contradict.', 'neutral']
    sns_plot.set_xticklabels([1,2,3], size=16)
    sns_plot.set_yticklabels(te_labels_short, size=14)
    fig = sns_plot.get_figure()
    fig.savefig("ontopic_plots/te_heatmap_"+source+"_"+model_source+".png", pad_inches=0.1, bbox_inches='tight', dpi=600)





if __name__ == "__main__":
    main()