import logging
import logging.config
import os
from pymongo import IndexModel, ASCENDING, DESCENDING, TEXT

import yaml

import mongo_utils

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

if __name__ == "__main__":

    mydb = mongo_utils.get_mongo_db()
    db_params = config_all['mongodb_params']
    for key in db_params:
        # for k in text_field:
        #     info[k] = _get_val_from_dot(record, text_field[k])
        try:
            # print(db_params[key])
            col_name = db_params[key]['name']
        except TypeError:
            col_name = None
        if col_name:
            index = db_params[key]['index']
            if index is not None:
                logger.info(f"Doing the index for {col_name}")
                for i in index:
                    logger.debug(f"FROM INDEX: {i}")
                    try:
                        # print(i['key'])
                        for k in i['key']:
                            if i['key'][k] == 1:
                                i['key'][k] = ASCENDING
                            elif i['key'][k] == -1:
                                i['key'][k] = DESCENDING
                            elif i['key'][k] == 'text':
                                i['key'][k] = TEXT

                        mydb[col_name].create_index(
                            i['key'].items(), **i['params'])
                        logger.info(
                            f"Done index on {i['key']} with params {i['params']}")
                    except KeyError:
                        logger.info(f"Done index on {i['key']} without params")
                        mydb[col_name].create_index(i['key'].items())
