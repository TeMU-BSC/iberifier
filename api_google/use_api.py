from googleapiclient.discovery import build
import json
import argparse
import os
import importlib.util
spec = importlib.util.spec_from_file_location("credentials", os.getcwd()+"/credentials.py")
credentials = importlib.util.module_from_spec(spec)
spec.loader.exec_module(credentials)
google_credentials = credentials.google_credentials


def get_arguments(parser):
    parser.add_argument("--query", default='vacunas', type=str, required=False)
    return parser

def main():
    parser = argparse.ArgumentParser()
    parser = get_arguments(parser)
    args = parser.parse_args()
    print(args)

    factCheckService = build("factchecktools", "v1alpha1", developerKey=google_credentials())
    request = factCheckService.claims().search(query=args.query,
                                                #reviewPublisherSiteFilter="Maldita.es",
                                                pageSize=1000000,#)
                                               languageCode="pt")# "es"
                                               #pageToken='CAs',
                                               # maxAgeDays='',
                                               #offset=10)
    response = request.execute()

    with open("results_{}.json".format(args.query), "w") as f:
        f.write(json.dumps(response))

if __name__ == '__main__':
    main()