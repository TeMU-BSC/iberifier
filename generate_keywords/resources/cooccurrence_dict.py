# import pymongo
import json
from collections import defaultdict
import string


# def open_collection():
#     myclient = pymongo.MongoClient('mongodb://127.0.0.1:27017/iberifier')
#     mydb = myclient.get_default_database()  # normalmente iberifier
#     mycol = mydb["cooccurrence"]
#     #if mycol.count_documents({}) != 0:
#     #    print('There are entries already.')
#     #    exit()
#     return mycol


def co_occurrence(sentences, window_size):
    d = defaultdict(int)
    vocab = set()
    for text in sentences:
        text = text.translate(str.maketrans("", "", string.punctuation))
        text = text.lower().split()
        # iterate over sentences
        for i in range(len(text)):
            token = text[i]
            vocab.add(token)  # add to vocab
            next_token = text[i + 1 : i + 1 + window_size]
            for t in next_token:
                key = tuple(sorted([t, token]))
                d[key] += 1
    return d


def main():
    # todo: use a corpus with also Catalan and Portuguese -> waiting for portuguese OSCAR
    text_file = open(
        "/home/blanca/Escriptori/projects/dt01/gpfs/scratch/bsc88/bsc88080/iberifier_corpora/large_trilingual.txt",
        "r",
    )  # 4000000 oscar_es + 4000000 oscar_ca + 4000000 oscar_pt
    lines = text_file.readlines()
    text_file.close()

    print(len(lines))

    counts = co_occurrence(lines, 2)

    list_counts = []
    for key, value in counts.items():
        if value > 10:
            list_counts.append({"words": list(key), "counts": value})
    print(len(list_counts))

    # to json
    with open("cooccurrence_dict.jsonl", "w") as f:
        f.write(json.dumps(list_counts) + "\n")

    # to mongo
    # collection = open_collection()
    # collection.insert_many(list_counts)


if __name__ == "__main__":
    main()
