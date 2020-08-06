import os, re
from rest_framework.exceptions import ValidationError

def resolve_google_credentials():
    path = os.environ['GOOGLE_APPLICATION_CREDENTIALS']
    if not os.path.exists( path ):
        credentials = os.environ['GOOGLE_SERVICE_KEY']#.replace("\\\\","\\")
        with open(path, 'w') as credentials_file:
            credentials_file.write( credentials )

def check_params(body, *args):
    msg = ''
    if body is None: 
        msg = 'request body as a json object, '
    else: 
        for prop in args: 
            if prop not in body: 
                msg += f'{prop}, '
    if msg: 
        msg = re.sub(r'(.*),', r'\1 and', msg[:-2])
        raise ValidationError('You must specify the ' + msg, 400)
    return body