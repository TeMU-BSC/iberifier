
How to run example:

```
python STS/dates_STS_filter.py --claim 642cba1057d061f04cd7b324 --source mynews --collection maldita

python STS/dates_STS_filter.py --claim 642cba1057d061f04cd7b324 --source tweets_new_call_strat --collection maldita
```

How to compare evaluations to STS models:

```
python sts_model_eval.py [DATA: news tweets] [MODEL: xlm_multi distiluse_multi spanish]
```