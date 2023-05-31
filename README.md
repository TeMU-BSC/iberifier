# Iberifier

## Pipeline

This pipeline is designed to be executed daily and gather data around disinformation. To this purpose, the pipeline takes the fact-checks that have been identified that day (through the APIs of Iberifier and Google), extracts keywords from these fact-checks, and uses these keywords to look for information related to these claims in digital media (MyNews service) and social networks (Twitter). 

To run the pipeline, you should have accounts for the Twitter and MyNews APIs. 

```
pip install -r requirements.txt

sh pipeline.sh
```
To change the configuration of the pipeline (e.g. the keyword or querying strategies, NLP models, etc.) see the config file in ```config/config.yaml```

## Evaluation

For the evaluation of the collection methods we have annotated some data manually. The scripts for the evaluation can be found in ```evaluation```.

## Classification

To assess the relation between the collected data and the fact-checked claims we have experimented some classification methods based in NLP. The experiments can be found in the folder ```classification```. The best models are already integrated in the pipeline with the script ```classification/classify_db.py```.

# Analysis


