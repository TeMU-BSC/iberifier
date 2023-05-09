
Evaluation of the collection:

```
python pairs_to_evaluate.py

prodigy textcat.manual iberifier_eval data/iberifier/data_to_evaluate.jsonl --label 'Difunde la claim falsa','Es sobre la claim pero no la apoya','Es sobre el tema pero no sobre la misma claim','Es otro tema','Tweet ilegible' --exclusive
prodigy db-out iberifier_eval

python evaluate_pipeline.py iberifier_eval.jsonl
```

Evaluation of the classification:

```
python pairs_second_round.py

prodigy textcat.manual second_round data/iberifier/second_round.jsonl --label 'Difunde la claim falsa','Es sobre la claim pero no la apoya','Es sobre el tema pero no sobre la misma claim','Es otro tema','Tweet ilegible' --exclusive
prodigy db-out second_round

python evaluate_pipeline.py second_round.jsonl
```