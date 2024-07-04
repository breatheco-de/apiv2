import requests, logging, os

logger = logging.getLogger(__name__)
API_URL = os.getenv("API_URL", "")


class GithubAuthException(Exception):
    pass


class Github:
    HOST = "https://api.github.com"
    headers = {}

    def __init__(self, token=None, org=None, host=None):
        self.token = token
        self.org = org
        self.page_size = 100
        if host is not None:
            self.HOST = host

    def get(self, action_name, request_data=None):

        if request_data is None:
            request_data = {}

        return self._call("GET", action_name, params=request_data)

    def head(self, action_name, request_data=None):

        if request_data is None:
            request_data = {}

        return self._call("HEAD", action_name, params=request_data)

    def post(self, action_name, request_data=None):

        if request_data is None:
            request_data = {}

        return self._call("POST", action_name, json=request_data)

    def delete(self, action_name, request_data=None):

        if request_data is None:
            request_data = {}

        return self._call("DELETE", action_name, params=request_data)

    def _call(self, method_name, action_name, params=None, json=None):

        self.headers = {
            "Authorization": "Bearer " + self.token,
            "Content-type": "application/json",
        }
        if method_name in ["GET", "DELETE"]:
            params = {
                # 'token': self.token,
                **params,
            }

        url = self.HOST + action_name
        resp = requests.request(method=method_name, url=url, headers=self.headers, params=params, json=json, timeout=2)

        if resp.status_code >= 200 and resp.status_code < 300:
            if method_name in ["DELETE", "HEAD"]:
                return resp

            data = resp.json()
            return data
        else:
            logger.debug(f"Error call {method_name}: /{action_name}")
            if resp.status_code == 401:
                raise GithubAuthException("Invalid credentials when calling the Github API")

            error_message = str(resp.status_code)
            try:
                error = resp.json()
                error_message = error["message"]
                logger.debug(error)
            except Exception:
                pass

            raise Exception(f"Unable to communicate with Github API for {action_name}, error: {error_message}")

    def get_machines_types(self, repo_name):
        return self.get(f"/repos/{self.org}/{repo_name}/codespaces/machines")

    def subscribe_to_repo(self, owner, repo_name, subscription_token):

        payload = {
            "name": "web",
            "active": True,
            "events": ["push"],
            "config": {"url": f"{API_URL}/v1/monitoring/github/webhook/{subscription_token}", "content_type": "json"},
        }
        return self.post(f"/repos/{owner}/{repo_name}/hooks", request_data=payload)

    def unsubscribe_from_repo(self, owner, repo_name, hook_id):
        return self.delete(f"/repos/{owner}/{repo_name}/hooks/{hook_id}")

    def file_exists(self, url):
        # Example URL: https://github.com/owner/repo/blob/branch/path/to/file
        # Extract necessary parts of the URL
        parts = url.split("/")
        owner = parts[3]
        repo_name = parts[4]
        branch = parts[6]
        path_to_file = "/".join(parts[7:])  # Join the remaining parts to form the path

        # Make a request to the GitHub API
        response = self.head(f"/repos/{owner}/{repo_name}/contents/{path_to_file}?ref={branch}")

        # Check if the file exists
        return response.status_code == 200

    def create_container(self, repo_name):
        return self.post(f"/repos/{self.org}/{repo_name}/codespaces")

    def get_org_members(self):
        results = []
        chunk = None
        while chunk is None or len(chunk) == self.page_size:
            chunk = self.get(
                f"/orgs/{self.org}/members",
                request_data={"per_page": self.page_size, "page": int(len(results) / self.page_size) + 1},
            )
            results = results + chunk

        return results

    def invite_org_member(self, email, role="direct_member", team_ids=None):

        if team_ids is None:
            team_ids = []

        return self.post(
            f"/orgs/{self.org}/invitations", request_data={"email": email, "role": role, "team_ids": [12, 26]}
        )

    def delete_org_member(self, username):
        return self.delete(f"/orgs/{self.org}/members/{username}")
