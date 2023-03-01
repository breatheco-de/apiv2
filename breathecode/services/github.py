import requests, logging

logger = logging.getLogger(__name__)


class Github:
    HOST = 'https://api.github.com'
    headers = {}

    def __init__(self, token=None, org=None, host=None):
        self.token = token
        self.org = org
        self.page_size = 100
        if host is not None:
            self.HOST = host

    def get(self, action_name, request_data={}):
        return self._call('GET', action_name, params=request_data)

    def post(self, action_name, request_data={}):
        return self._call('POST', action_name, json=request_data)

    def _call(self, method_name, action_name, params=None, json=None):

        self.headers = {
            'Authorization': 'Bearer ' + self.token,
            'Content-type': 'application/json',
        }
        if method_name == 'GET':
            params = {
                # 'token': self.token,
                **params,
            }

        url = self.HOST + action_name
        resp = requests.request(method=method_name,
                                url=url,
                                headers=self.headers,
                                params=params,
                                json=json,
                                timeout=2)

        if resp.status_code == 200:
            data = resp.json()
            # if data['ok'] == False:
            #     raise Exception('Github API Error ' + data['error'])
            # else:
            logger.debug(f'Successfull call {method_name}: /{action_name}')
            return data
        else:
            print(url, resp.json())
            raise Exception(f'Unable to communicate with Github API, error: {resp.status_code}')

    def get_machines_types(self, repo_name):
        return self.get(f'/repos/{self.org}/{repo_name}/codespaces/machines')

    def create_container(self, repo_name):
        return self.post(f'/repos/{self.org}/{repo_name}/codespaces')

    def get_org_members(self):
        results = []
        chunk = None
        while chunk is None or len(chunk) == self.page_size:
            chunk = self.get(f'/orgs/{self.org}/members',
                             request_data={
                                 'per_page': self.page_size,
                                 'page': int(len(results) / self.page_size) + 1
                             })
            results = results + chunk

        return results

    def invite_org_member(self, email, role='direct_member', team_ids=[]):
        return self.post(f'/orgs/{self.org}/invitations',
                         request_data={
                             'email': email,
                             'role': role,
                             'team_ids': [12, 26]
                         })

    def delete_org_member(self, username):
        return self.delete(f'/orgs/{self.org}/members/{username}')
