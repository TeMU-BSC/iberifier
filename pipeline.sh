
# get the daily fact-checks from google and maldita
python api_google/use_api.py --query daily
python api_maldita/use_api.py --query daily

# get keywords related to these fact-checks
KEYWORDS=$()

# get tweets that could be related to the fact-checks


# get news that could be related to this fact-checks
python mynews/use_api.py --query $KEYWORDS