
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
python mynews/use_api.py --auto_query --max auto
