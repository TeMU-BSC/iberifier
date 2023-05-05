import sys
import os
import tqdm
import yaml

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from mongo_utils import mongo_utils

from datetime import datetime, timedelta
from sentence_transformers import SentenceTransformer, util
from transformers import pipeline, AutoTokenizer

import logging
import logging.config

logger = logging.getLogger(__name__)

# Load config and credentials

config_path = os.path.join(os.path.dirname(
    __file__), '../config', 'config.yaml')
config_all = yaml.safe_load(open(config_path))


logging_config_path = os.path.join(os.path.dirname(
    __file__), '../config', config_all['logging']['logging_filename'])
with open(logging_config_path,  "r") as f:
    yaml_config = yaml.safe_load(f.read())
    logging.config.dictConfig(yaml_config)

logger = logging.getLogger(config_all['logging']['level'])


def get_source_keys(source):
    """Defines the right fields for each source"""
    source_keys = {}
    # if source == "telegram":
    #     source_keys["date"] = "date"
    #     source_keys["text"] = "message"
    if source == "tweets" or source == "tweets_new_call_strat":
        source_keys["date"] = "date"
        source_keys["text"] = "text"
    # elif source == "lusa":
    #     source_keys["date"] = "date"
    #     source_keys["text"] = "headline"
    elif source == "mynews":
        source_keys["date"] = "date"
        source_keys["text"] = "Title"
    return source_keys

def get_claim_ids(db, source, tag, date_limit, finer=False):
    collection = db[source]
    results = [i['_id'] for i in collection.find({"date": {"$gt": date_limit}, tag: {"$exists": False}, "calification": "Falso"})]
    return results

def get_claims(db, tag, date_limit, finer=False):
    list_ids = get_claim_ids(db, 'keywords', tag, date_limit=date_limit, finer=finer)
    tqdm_length = len(list_ids)
    cursor = db['keywords'].find({'_id': {"$in": list_ids}}, batch_size=1)
    for record in tqdm.tqdm(cursor, total=tqdm_length):
        yield record
    cursor.close()

def get_list_ids(db, source, claim_id, finer=False):
    collection = db[source]
    if finer:
        results = [i['_id'] for i in collection.find({'fact_id': claim_id, 'claim_relation':'on-topic'})]
    else:
        results = [i['_id'] for i in collection.find({'fact_id': claim_id})]
    return results

def get_messages(db, claim, source, finer=False):
    print(claim['fact_id'])
    source_keys = get_source_keys(source)
    list_ids = get_list_ids(db, source, claim['fact_id'], finer)
    tqdm_length = len(list_ids)
    cursor = db[source].find({'_id': {"$in": list_ids}}, batch_size=1)
    for record in tqdm.tqdm(cursor, total=tqdm_length):
        yield record, source_keys
    cursor.close()

def prepare(sentence_pairs, tokenizer):
    sentence_pairs_prep = []
    for s1, s2 in sentence_pairs:
        sentence_pairs_prep.append(f"{tokenizer.cls_token} {s1}{tokenizer.sep_token}{tokenizer.sep_token} {s2}{tokenizer.sep_token}")
    return sentence_pairs_prep

def classify_claims(db, claims, source, task, tag, method, chosen_model, threshold, finer=False):
    # choose labels
    if task == 'topic_relation':
        labels = ['on-topic', 'off-topic']
    elif task == 'claim_relation':
        labels = ['on-claim', 'off-claim']
    elif task == 'claim_finer_relation':
        labels = ['disseminates', 'not-disseminates']
    else:
        labels = ['','']
        print('Such classification is not implemented.')

    # choose a model
    if chosen_model == 'distiluse_multi':
        model = SentenceTransformer('sentence-transformers/distiluse-base-multilingual-cased')
    elif chosen_model == 'paraph':
        model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-mpnet-base-v2')
    elif chosen_model == 'supervised_sts':
        path_sts = 'models/roberta-base-bne-sts'
        tokenizer_sts = AutoTokenizer.from_pretrained(path_sts)
        model = pipeline('text-classification', model=path_sts, tokenizer=tokenizer_sts, truncation=True)
    else:
        print('There is no such model.')
        exit()

    for claim_record in claims:
        for doc,source_keys in get_messages(db, claim_record, source, finer):
            if finer:
                try:
                    c_embeddings = model.encode([claim_record['claim'], doc[source_keys["text"]]], convert_to_tensor=True)
                    c_sim = util.cos_sim(c_embeddings[0], c_embeddings[1])

                    f_embeddings = model.encode([claim_record['fact-check'], doc[source_keys["text"]]], convert_to_tensor=True)
                    f_sim = util.cos_sim(f_embeddings[0], f_embeddings[1])

                    if c_sim > f_sim:
                        db[source].update_one({"_id": doc['_id']},
                                              {"$set": {task: labels[0]}})
                    else:
                        db[source].update_one({"_id": doc['_id']},
                                              {"$set": {task: labels[1]}})
                except KeyError:
                    print('There is no claim or fact-check in this entry')
                    break
            else:
                try:
                    if method == 'SentenceTransformers':
                        embeddings = model.encode([claim_record['claim'], doc[source_keys["text"]]], convert_to_tensor=True)
                        sim = util.cos_sim(embeddings[0], embeddings[1])
                    elif method == 'supervised':
                        predictions = model(prepare([(claim_record['claim'], doc[source_keys["text"]])], tokenizer_sts), add_special_tokens=False)
                        sim = predictions[0]['score']
                    else:
                        print('There is no such method.')
                        exit()

                    if sim > threshold:
                        db[source].update_one({"_id": doc['_id']},
                                                            {"$set": {task: labels[0]}})
                    else:
                        db[source].update_one({"_id": doc['_id']},
                                                        {"$set": {task: labels[1]}})
                except KeyError:
                    print('There is no claim in this entry')
                    break

        # update the claim witht a tag so it does not rerun
        db['keywords'].update_one({"_id": claim_record['_id']}, {"$set": {tag: datetime.now()}})


def main():
    source = sys.argv[1]
    task = sys.argv[2]
    method = config_all["classification_params"][source][task]["method"]
    chosen_model = config_all["classification_params"][source][task]["chosen_model"]
    threshold = config_all["classification_params"][source][task]["threshold"]
    date_limit = datetime(2023, 3, 15) #config_all["classification_params"][source]["date_limit"]


    tag = source+'_'+task+'_already_done'

    # connect to the mongo db
    logger.info("Connecting to the db")
    db_iberifier = mongo_utils.get_mongo_db()

    # look for all the claims that have not been classified yet, add date limit for the search
    logger.info("Getting claims")
    claims = get_claims(db_iberifier, tag, date_limit)

    logger.info("Classifying {} by {}".format(source, task))
    #classify_claims(db_iberifier, claims, source, task, tag, method, chosen_model, threshold)

    if task == 'claim_relation':
        additional_task = 'claim_finer_relation'
        new_tag = source+'_'+additional_task+'_already_done'
        new_method = config_all["classification_params"][source][additional_task]["method"]
        new_chosen_model = config_all["classification_params"][source][additional_task]["chosen_model"]
        claims = get_claims(db_iberifier, additional_task, date_limit, finer=True)
        classify_claims(db_iberifier, claims, source, additional_task, new_tag, new_method, new_chosen_model, threshold=None, finer=True)




if __name__ == "__main__":
    main()
