import spacy
import textacy
from collections import Counter
import pymongo
import json

# python -m spacy download es_core_news_sm
nlp = spacy.load("es_core_news_sm")

def open_collection():
    myclient = pymongo.MongoClient('mongodb://127.0.0.1:27017/iberifier')
    mydb = myclient.get_default_database()  # normalmente iberifier
    mycol = mydb["cooccurrence"]
    #if mycol.count_documents({}) != 0:
    #    print('There are entries already.')
    #    exit()
    return mycol

def main():
    text_file = open("/home/blanca/Escriptori/projects/dt01/gpfs/projects/bsc88/corpora/oscar_es/v1/s4/oscar_es_45M_docs_clean_20210716.txt", "r") #oscar_es_45M_docs_clean_20210716
    data = text_file.read()
    text_file.close()
    #print(data)

    # tokenize
    doc = nlp(data)
    ngrams = list(textacy.extract.basics.ngrams(doc, 2, min_freq=2))
    str_ngrams = [str(i).lower() for i in ngrams]

    counts = dict(Counter(str_ngrams))

    # create dict
    list_counts = []
    for key, value in counts.items():
        list_counts.append({'words': key.split(' '), 'counts': value})
    #print(list_counts)

    # to json
    with open("cooccurrence_dict.jsonl", "w") as f:
        f.write(json.dumps(list_counts) + "\n")

    #to mongo
    #collection = open_collection()
    #collection.insert_many(list_counts)


if __name__ == '__main__':
    main()