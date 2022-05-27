import pymongo, os

# Credential loading
import importlib.util
spec = importlib.util.spec_from_file_location("credentials", os.getcwd()+"/credentials.py")
credentials = importlib.util.module_from_spec(spec)
spec.loader.exec_module(credentials)
mongodb_credentials = credentials.mongodb_credentials

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
    if _mongoclient == None:
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
        _mongoclient = pymongo.MongoClient(host, port, username=user, password=passw)
    return _mongoclient