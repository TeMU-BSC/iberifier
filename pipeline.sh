#!/bin/bash

source venv/bin/activate

# get the daily fact-checks from google and maldita
python api_google/use_api.py
python api_maldita/use_api.py

# create the NER and POS
python generate_keywords/entities_extraction.py 

# create keywords for search
python generate_keywords/keyword_processor.py

# get tweets that could be related to the fact-checks
python api_twitter/search_from_keys.py

# get news that could be related to this fact-checks
python mynews/use_api.py
# remove the false truths in mynews by looking for at least one matched key
python mynews/keywords_refilter.py

# classify if the tweets and news are or not on topic
python classification/classify_db.py mynews topic_relation
python classification/classify_db.py tweets_new_call_strat topic_relation
python classification/classify_db.py tweets_new_call_strat claim_relation

