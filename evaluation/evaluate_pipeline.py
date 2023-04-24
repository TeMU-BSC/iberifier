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

for label, entry in count.items():
    print(label, '&', entry, '\\\\')
print('\\toprule')
print('TOTAL &', len(data))
