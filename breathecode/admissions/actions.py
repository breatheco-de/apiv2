import requests, os
from google.cloud import storage
from urllib.parse import urlencode

BUCKET_NAME = "admissions-breathecode"

def resolve_google_credentials():
    path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS',None)
    if path is None or not os.path.exists( path ):
        credentials = os.getenv('GOOGLE_SERVICE_KEY')#.replace("\\\\","\\")
        with open(path, 'w') as credentials_file:
            credentials_file.write( credentials )

def remove_bucket_object(file_name=None):
    if file_name is None or file_name == "":
        return False

    resolve_google_credentials()
    client = storage.Client()
    bucket = client.bucket(BUCKET_NAME)
    blob = bucket.get_blob(file_name)
    blob.delete()

    return True

def get_bucket_object(file_name):
    if file_name is None or file_name == "":
        return False

    resolve_google_credentials()
    client = storage.Client()
    bucket = client.bucket(BUCKET_NAME)
    blob = bucket.get_blob(file_name)
    return blob
