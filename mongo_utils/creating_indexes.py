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
    db_params = config_all['mongodb_params']
    for key in db_params:
        try:
            print(db_params[key])
            col_name = db_params[key]['name']
            index = db_params[key]['index']
            if index is not None:
                for i in index:
                    try:
                        mydb[col_name].create_index(i['key'], i['params'])
                    except KeyError:
                        mydb[col_name].create_index(i['key'])
        except TypeError:
            pass
