
import requests
import os
import importlib.util
import argparse

cred_path = os.path.join(os.path.dirname(__file__), "../credentials.py")
spec = importlib.util.spec_from_file_location("credentials", cred_path)
credentials = importlib.util.module_from_spec(spec)
spec.loader.exec_module(credentials)
mynews_credentials = credentials.mynews_credentials

def get_arguments(parser):
    parser.add_argument("--query", default="(BSC AND BARCELONA) OR (BSC AND MADRID)", type=str, required=False, help="the tokens to query")
    parser.add_argument("--fromD", default="1654321118", type=str, required=False)
    parser.add_argument("--toD", default="1656913073", type=str, required=False)
    parser.add_argument("--topic", default="13", type=str, required=False)
    parser.add_argument("--max", default="2", type=str, required=False)
    return parser

def get_token():
    public_key, password = mynews_credentials()
    files = {
        'public_key': (None, public_key),
        'password': (None, password),
    }
    TOKEN = requests.post('https://api.mynews.es/api/token/', files=files)
    return TOKEN

def query(token, args):
    headers = {
        'Authorization': f"Bearer {token.text}",
    }

    files = {
        'query': (None, args.query),
        'fromTime': (None, args.fromD),
        'toTime': (None, args.toD),
        'agrupations': (None, args.topic),
        'maxResults': (None, args.max),
    }

    response = requests.post('https://api.mynews.es/api/hemeroteca/', headers=headers, files=files)

    return response.json()

def main():
    parser = argparse.ArgumentParser()
    parser = get_arguments(parser)
    args = parser.parse_args()
    print(args)

    token = get_token()
    result = query(token, args)

    for element in result['news']:
        print(element['Title'])

if __name__ == "__main__":
    main()
