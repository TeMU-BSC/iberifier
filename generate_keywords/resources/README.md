
Al servidor dt:
```
head -n 4000000 oscar_ca/v1/s2/oscar_ca_20200915_cleaned_20201118.txt > oscar_ca/v1/s2/trial.txt
 
head -n 4000000  oscar_es/v1/s4/oscar_es_20200127_sentence_split_20200901.txt >  oscar_es/v1/s4/trial.txt
 
head -n 4000000 paracrawl_pt/v1/s1/paracrawl_pt.txt > paracrawl_pt/v1/s1/trial.txt

cat oscar_es/v1/s4/trial.txt oscar_ca/v1/s2/trial.txt paracrawl_pt/v1/s1/trial.txt > berifier_corpora/large_trilingual.txt
```

En local:
```
python cooccurrence_dict.py
```

Al servidor de iberifier:
```
mongoimport --jsonArray --db iberifier --collection cooccurrence --file generate_keywords/resources/cooccurrence_dict.jsonl
```