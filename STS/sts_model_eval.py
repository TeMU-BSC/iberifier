
import json
import sys
from sentence_transformers import SentenceTransformer
from scipy import spatial
import numpy as np
import matplotlib.pyplot as plt
#import seaborn as sns

def main():
    source = sys.argv[1] # news tweets
    model_source = sys.argv[2]

    with open('../data/eval_'+source+'.jsonl') as f:
        data = []
        for line in f:
            data.append(json.loads(line))

    # mapping_labels = {'Difunde la claim falsa': 1,
    #                   'Es sobre la claim pero no la apoya': 0.75,
    #                   'Es sobre el tema pero no sobre la misma claim': 0.50,
    #                     'Es otro tema': 0.25,
    #                     'Tweet ilegible': 0}
    mapping_labels = {'The text disseminates the false claim':0,
                 'The text is about the claim, but it does not support it':0.25,
                 'The text is on topic but not about this precise claim':0.50,
                 'The text is on another topic':0.75,
                 'The text is not readable':1}

    if model_source == 'xlm_multi':
        model = SentenceTransformer('sentence-transformers/stsb-xlm-r-multilingual')
    elif model_source == 'distiluse_multi':
        model = SentenceTransformer('sentence-transformers/distiluse-base-multilingual-cased')
    elif model_source == 'spanish':
        model = SentenceTransformer('hiiamsid/sentence_similarity_spanish_es')
    else:
        print('There is no such model.')
        exit()

    #claim_ids = [line["id_claim"] for line in data]
    #unique_claim_ids = list(set(claim_ids))
    all_sts_values = []
    #all_label_values = []
    for label in mapping_labels.keys():
        sts_values = []
        label_values = []
        for line in data:
            if label == line['label_eng']:
                embeddings = model.encode([line['claim'], line['text']])
                dist = spatial.distance.cosine(embeddings[0], embeddings[1])
                sts_values.append(dist)
                #sts_values.append(1)
                label_values.append(mapping_labels[line['label_eng']])
        print(label)
        print(len(sts_values))
        print(np.mean(sts_values))
        #all_sts_values.extend(sts_values)
        all_sts_values.append(sts_values)
        #all_label_values.extend(label_values)
    #print(np.corrcoef(all_sts_values, all_label_values))

    # plt.scatter(
    #     x=all_sts_values,
    #     y=all_label_values,
    #     c=all_lab,
    # )
    #plt.yticks(list(mapping_labels.values()),
    #           list(mapping_labels.keys()))

    f = plt.figure()
    f.set_figwidth(9)
    plt.rc('xtick', labelsize=6)
    violin_plot = plt.violinplot(all_sts_values[::-1], vert = False, showmedians=True)
    if source == 'news':
        plt.xlabel('Distance from Claim to Title')
    else:
        plt.xlabel('Distance from Claim to Tweet')
    #plt.ylabel('Distance from Claim to Title')
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