
import json

def main():
    with open('trial.json', 'r') as f:
        data = json.load(f)

    for element in data['news']:
        print(element.keys())

main()