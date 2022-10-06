import logging
import os

import yaml

import mongo_utils

logger = logging.getLogger(__name__)

# Load config and credentials

config_path = os.path.join(os.path.dirname(
    __file__), '../config', 'config.yaml')
config_all = yaml.safe_load(open(config_path))


if __name__ == "__main__":

    mydb = mongo_utils.get_mongo_db()
    print(mydb)
    indexes = {'tweets': config_all['mongodb_params']['tweets'],
               'google': config_all['mongodb_params']['google'],
               'maldita': config_all['mongodb_params']['maldita'],
               'mynews': config_all['mongodb_params']['mynews'],
               'cooccurrence': config_all['mongodb_params']['cooccurrence']}
    for entry in indexes:
        print(indexes[entry])
        col_name = indexes[entry]['name']
        dict_index = indexes[entry]['index']
        try:
            index = [(k, dict_index[k]) for k in dict_index]
            print(index)
            mydb[col_name].create_index(index)
        except TypeError:
            pass
