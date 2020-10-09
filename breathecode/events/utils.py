import os, requests


class Eventbrite(object):

    def __init__(self, token = None):
        if token is None:
            token = os.getenv('EVENTBRITE_KEY',None)

        self.token = token
        
    def get_organization_events(self):
        pass