import csv
import requests
import os
import re
from unicodedata import combining, normalize
import sys
import yaml

import logging.config

import logging

# cred_path = os.path.join(os.path.dirname(__file__), "../credentials.py")
# spec = importlib.util.spec_from_file_location("credentials", cred_path)
# credentials = importlib.util.module_from_spec(spec)
# spec.loader.exec_module(credentials)
# mynews_credentials = credentials.mynews_credentials


sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from mongo_utils import mongo_utils

logger = logging.getLogger(__name__)

# Load config and credentials

config_path = os.path.join(os.path.dirname(
    __file__), '../config', 'config.yaml')
config_all = yaml.safe_load(open(config_path))


logging_config_path = os.path.join(os.path.dirname(
    __file__), '../config', config_all['logging']['logging_filename'])
with open(logging_config_path,  "r") as f:
    yaml_config = yaml.safe_load(f.read())
    logging.config.dictConfig(yaml_config)

logger = logging.getLogger(config_all['logging']['level'])


mynews_cred_path = os.path.join(
    os.path.dirname(__file__),
    "../config",
    config_all["api_mynews_params"]["cred_filename"],
)
mynews_credentials = yaml.safe_load(open(mynews_cred_path))[
    "mynews_api_credentials"]


def normalize_string(s):
    return "".join(c for c in normalize("NFD", s.lower()) if not combining(c))


def get_token(public_key, password):
    files = {
        'public_key': (None, public_key),
        'password': (None, password),
    }
    TOKEN = requests.post('https://api.mynews.es/api/token/', files=files)
    return TOKEN


def query(token):

    headers = {
        'Authorization': f"Bearer {token.text}",
    }

    response = requests.post(
        'https://api.mynews.es/api/publicaciones/', headers=headers)

    return response.json()


def main():
    api_key = mynews_credentials['public_key']
    api_password = mynews_credentials['password']
    # import the navarra media list
    with open('./mynews/BD_DIGITALMEDIA_SPAIN_2021.csv') as f:
        reader = csv.reader(f)
        data = []
        # next(reader)
        for line in reader:
            data.append(line)

    # view info in media list to decide what to use to filter
    for i in range(0, 73):
        print('Index:', i, 'Field:', data[0][i], 'Example value:', data[1][i])

    navarra_media_names = {}
    for line in data[1:]:
        if line[2] == 'activo':  # and line[7] == 'periodístico' and line[31] == 'nacional' and line[26] == "1": # here we add the filters!!!
            navarra_media_names[line[0].lower()] = line[72]
            url = line[1]
            pre = re.findall('http[s]?:\/\/[w\.]{0,4}', url)
            if not pre:
                pre = ['']
            part_url = url[len(pre[0]):len(url)].replace(r'/', '')
            navarra_media_names[part_url] = line[72]

    # call from the list of media in the mynews API
    token = get_token(api_key, api_password)
    result = query(token)
    print(len(result))

    # get the names of the media
    mynews_media_names = {}
    for line in result:
        mynews_media_names[line['nombre']] = line['ref']

    # match so that it detects which media are the same
    matches = {}
    for i in mynews_media_names:
        if i.lower() in navarra_media_names:
            matches[mynews_media_names[i]] = navarra_media_names[i.lower()]

        i_parts = i.split(' - ')
        for part in i_parts:
            if part.lower() in navarra_media_names:
                matches[mynews_media_names[i]
                        ] = navarra_media_names[part.lower()]

        i_other_parts = i.split('  ')
        for part in i_other_parts:
            if part.lower() in navarra_media_names:
                matches[mynews_media_names[i]
                        ] = navarra_media_names[part.lower()]

        i_other2_parts = i.split('/')
        for part in i_other2_parts:
            if part.lower() in navarra_media_names:
                matches[mynews_media_names[i]
                        ] = navarra_media_names[part.lower()]

        if normalize_string(i) in navarra_media_names:
            matches[mynews_media_names[i]
                    ] = navarra_media_names[normalize_string(i)]

    print(len(matches))
    no_matches = [i for i in mynews_media_names if i not in matches]
    # print(matches)
    # print(no_matches)
    print(len(no_matches))

    with open('mynews/matching_list.csv', 'w') as out:
        writer = csv.writer(out)
        for line in matches:
            writer.writerow([line, matches[line]])


main()
