import json
from collections import Counter
import sys

with open(sys.argv[1]) as f:
    data = []
    for line in f:
        data.append(json.loads(line))

print(len(data))
evaluation = []
for line in data:
    try:
        evaluation.append(line['accept'][0])
    except IndexError:
        print(line)

count = Counter(evaluation)
print(count)
for label, entry in count.items():
    print(label, '&', entry, '\\\\')
print('\\toprule')
print('TOTAL &', len(data))

claim_ids = [line["_id"].split('_')[1] for line in data]
unique_claim_ids = list(set(claim_ids))


for claim_id in unique_claim_ids:
    claim_data = []
    claim = ''
    for entry in data:
        if entry["_id"].split('_')[1] == claim_id:
            claim = entry['text'].split(':')[1]
            claim_data.append(entry['accept'][0])
    print(claim[:-16])
    print(Counter(claim_data))

