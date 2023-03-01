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

def remove_spaces(in_string: str):
    return in_string.translate(str.maketrans({' ': ''}))

def name_to_url(s):
    normalized = normalize_string(s)
    no_space = remove_spaces(normalized).lower()
    return no_space

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
    with open('mynews/digitalmedia_22_02_23.csv') as f:
        reader = csv.reader(f)
        data = []
        # next(reader)
        for line in reader:
            data.append(line)

    # view info in media list to decide what to use to filter
    #for i in range(0, 73):
    #    print('Index:', i, 'Field:', data[0][i], 'Example value:', data[1][i])

    url_col = 3 # 1
    name_col = 1 # 0
    id_col = 0 # 72
    navarra_media_names = {}
    for line in data[1:]:
        if line[name_col] and line[2] == 'true' and line[16] == 'ES':  # and line[7] == 'periodístico' and line[31] == 'nacional' and line[26] == "1": # here we add the filters!!!
            navarra_media_names[line[name_col].lower()] = line[id_col]
            url = line[url_col]
            pre = re.findall('http[s]?:\/\/[w\.]{0,4}', url)
            if not pre:
                pre = ['']
            part_url = url[len(pre[0]):len(url)].replace(r'/', '')
            navarra_media_names[part_url] = line[id_col]
            no_ending_url = part_url.split('.')[0]
            navarra_media_names[no_ending_url] = line[id_col]
            navarra_media_names[normalize_string(line[name_col])] = line[id_col]
            navarra_media_names[name_to_url(line[name_col])] = line[id_col]

    # call from the list of media in the mynews API
    token = get_token(api_key, api_password)
    result = query(token)
    #print(len(result))

    # get the names of the media
    mynews_media_names = {}
    for line in result:
        mynews_media_names[line['nombre']] = line['ref']

    # match so that it detects which media are the same
    counter = 0
    matches = {}
    not_matching = []
    print(len(mynews_media_names))
    for i in mynews_media_names:
        found_match = False
        if i.lower() in navarra_media_names:
            matches[mynews_media_names[i]] = navarra_media_names[i.lower()]
            found_match = True

        list_separators = ['/', ' - ', '  ', '. Ed. ', ' de ', ' en ',' Ed. ']
        for sep in list_separators:
            i_parts = i.split(sep)
            for part in i_parts:
                if part.lower() in navarra_media_names:
                    matches[mynews_media_names[i]
                            ] = navarra_media_names[part.lower()]
                    found_match = True

        if normalize_string(i) in navarra_media_names:
            matches[mynews_media_names[i]
            ] = navarra_media_names[normalize_string(i)]
            found_match = True

        if name_to_url(i) in navarra_media_names:
            matches[mynews_media_names[i]] = navarra_media_names[name_to_url(i)]
            found_match = True

        if len(i) > 3:
            remove_last = i.split(' ')[:-1]
            if "".join(remove_last).lower() in navarra_media_names:
                matches[mynews_media_names[i]] = navarra_media_names["".join(remove_last).lower()]
                found_match = True
            if " ".join(remove_last).lower() in navarra_media_names:
                matches[mynews_media_names[i]] = navarra_media_names[" ".join(remove_last).lower()]
                found_match = True

        if i.split('.')[0] in navarra_media_names:
            matches[mynews_media_names[i]] = navarra_media_names[i.split('.')[0]]
            found_match = True

        if found_match:
            counter += 1
        else:
            not_matching.append(i)

    print(counter)

    with open('mynews/matching_list.csv', 'w') as out:
        writer = csv.writer(out)
        for line in matches:
            writer.writerow([line, matches[line]])

    with open('mynews/not_matched_media.txt', 'w') as out:
        for line in not_matching:
            out.write(line+'\n')


main()
