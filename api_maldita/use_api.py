
import requests
import argparse
import json
import importlib.util
spec = importlib.util.spec_from_file_location("credentials", "/home/blanca/prova/credentials.py")
credentials = importlib.util.module_from_spec(spec)
spec.loader.exec_module(credentials)
maldita_api = credentials.maldita_api

def get_arguments(parser):
    parser.add_argument("--query", default='https://repositorio.iberifier.eu/api/contents?page=1&itemsPerPage=30', type=str, required=False)
    return parser

def main():
    parser = argparse.ArgumentParser()
    parser = get_arguments(parser)
    args = parser.parse_args()
    print(args)

    user, key = maldita_api()
    response = requests.get(args.query, auth=requests.auth.HTTPBasicAuth(user, key))

    with open("results_{}.json".format('prova'), "w") as f:
        f.write(json.dumps(response.json()))

if __name__ == '__main__':
    main()