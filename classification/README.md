
How to run example from the DB:

```
python classification/dates_STS_filter.py --claim 642cba1057d061f04cd7b324 --source mynews --collection maldita

python classification/dates_STS_filter.py --claim 642cba1057d061f04cd7b324 --source tweets_new_call_strat --collection maldita
```

How to compare evaluations to STS models and choose the best threshold:

```
cd classification
sh compare_sts_models.sh
```