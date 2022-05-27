# Iberifier

## Data sources and associated schema:
### Twitter API:
### Telegram API:
### [Meneame](https://www.meneame.net/): 

## Fact checks and associated schema:
### Maldita API:

All the historical data to the db:
```
python api_maldita/use_api.py --query historical
```

### Google Fake news API
* The documentation from Google Fake News API: [here](https://developers.google.com/search/docs/advanced/structured-data/factcheck#type_definitions)

All the historical data to the db:
```
python api_google/use_api.py --query historical
```

## MongoDB structure


## Initial setup


### PLANTL-GOB-ES
The models for the NER extraction using the TeMU ES needs to be cloned from huggingface rather than using the pipelin. The reason is the need to modify the config file to replace the `_` with `-` for the entities identification. It should not be needed for the other models

```bash
cd ./models/
git lfs install
git clone https://huggingface.co/PlanTL-GOB-ES/roberta-base-bne-capitel-ner-plus
```
