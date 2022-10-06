# Credential loading
# import importlib.util
import os

import yaml
import pymongo

# cred_path = os.path.join(os.path.dirname(__file__), "../credentials.py")
# spec = importlib.util.spec_from_file_location("credentials", cred_path)
# credentials = importlib.util.module_from_spec(spec)
# spec.loader.exec_module(credentials)
# mongodb_credentials = credentials.mongodb_credentials()

config_path = os.path.join(os.path.dirname(__file__), '../config', 'config.yaml')
config_all = yaml.safe_load(open(config_path))

mongo_cred_path = os.path.join(
    os.path.dirname(__file__),
    "../config",
    config_all["mongodb_params"]["mongodb_cred_filename"],
)
mongodb_credentials = yaml.safe_load(open(mongo_cred_path))[
    "mongodb_credentials"]

# Global client
global _mongoclient
_mongoclient = None


def get_mongo_db(db=None):
    """
    Gets the specified Mongo database.
    If not specified, gets the default database from the credentials file.
    """
    if db:
        database = db
    else:
        database = mongodb_credentials["DB_MONGO_DATABASE"]
    client = get_client()
    return client[database]


def get_client():
    """
    Gets the MongoClient Object. If Mongo is not connected, connects.
    """
    global _mongoclient
    if _mongoclient is None:
        host = mongodb_credentials["DB_HOST"]

        port = int(mongodb_credentials["DB_MONGO_PORT"])
        try:
            user = mongodb_credentials["DB_MONGO_USER"]
        except KeyError:
            user = None
        try:
            passw = mongodb_credentials["DB_MONGO_PASS"]
        except KeyError:
            passw = None
        _mongoclient = pymongo.MongoClient(
            host, port, username=user, password=passw)
    return _mongoclient
