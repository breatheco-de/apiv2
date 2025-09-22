import logging
import os
from typing import Generator, Optional

import requests

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

        url = self.HOST + action_name
        resp = requests.request(method=method_name, url=url, headers=self.headers, params=params, json=json, timeout=20)

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

            raise Exception(
                f"Unable to communicate with Github API for {method_name} {action_name}, error: {error_message}"
            )

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

    def parse_github_url(self, url):
        """
        Parse various GitHub URL patterns to extract repository information and
        detect whether the target is a file (and if it's an image).
    
        Supported URL patterns:
        - https://github.com/owner/repo/blob/branch/path/to/file
        - https://github.com/owner/repo/issues/123
        - https://github.com/owner/repo/pull/456
        - https://raw.githubusercontent.com/owner/repo/branch/path/to/file
        - https://raw.githubusercontent.com/owner/repo/branch/path/to/file?token=...
        - https://api.github.com/repos/owner/repo/contents/path/to/file
    
        Returns dict or None:
            {
                'owner': str,
                'repo': str,
                'branch': str|None,
                'path': str|None,
                'url_type': 'blob'|'raw'|'api'|'issue'|'pull'|'repo',
                'is_file': bool,     # True when URL points to a file path
                'is_image': bool,    # True when file extension matches known image types
                'ext': str|None      # Lowercase extension without dot (e.g., 'png')
            }
        """
        if not url:
            return None
    
        # Known image extensions (lowercase, no dot)
        IMAGE_EXTS = {
            "png", "jpg", "jpeg", "gif", "bmp", "tif", "tiff", "webp",
            "svg", "ico", "heic", "heif", "avif", "jfif"
        }
    
        def strip_query_fragment(p: str) -> str:
            # Remove ?query and #fragment
            p = p.split("?", 1)[0]
            p = p.split("#", 1)[0]
            return p
    
        def ext_from_path(p: str) -> str | None:
            if not p:
                return None
            p = strip_query_fragment(p)
            _, ext = os.path.splitext(p)
            return ext[1:].lower() if ext else None
    
        def finalize(result: dict) -> dict:
            # Derive is_file/is_image/ext from path + url_type
            path = result.get("path")
            url_type = result.get("url_type")
    
            # Heuristic: blob/raw/api contents with a non-empty path are files.
            is_file = bool(path) and url_type in {"blob", "raw", "api"}
            ext = ext_from_path(path) if is_file else None
            is_image = bool(ext and ext in IMAGE_EXTS)
    
            result["is_file"] = is_file
            result["is_image"] = is_image
            result["ext"] = ext
            return result
    
        try:
            # github.com paths
            if "github.com" in url and "raw.githubusercontent.com" not in url and "api.github.com" not in url:
                parts = url.split("/")
                if len(parts) < 5:
                    return None
    
                owner = parts[3]
                repo = parts[4]
    
                result = {"owner": owner, "repo": repo, "branch": None, "path": None, "url_type": "repo"}
    
                if len(parts) > 5:
                    if parts[5] == "blob" and len(parts) > 6:
                        result["url_type"] = "blob"
                        result["branch"] = parts[6]
                        if len(parts) > 7:
                            # Join remaining as path (keep potential ?raw, we'll strip later)
                            result["path"] = "/".join(parts[7:])
                    elif parts[5] == "issues":
                        result["url_type"] = "issue"
                    elif parts[5] == "pull":
                        result["url_type"] = "pull"
    
                return finalize(result)
    
            # raw.githubusercontent.com
            elif "raw.githubusercontent.com" in url:
                clean_url = url.split("?")[0]
                parts = clean_url.split("/")
                if len(parts) < 6:
                    return None
    
                owner = parts[3]
                repo = parts[4]
                branch = parts[5]
                path = "/".join(parts[6:]) if len(parts) > 6 else None
    
                return finalize({
                    "owner": owner,
                    "repo": repo,
                    "branch": branch,
                    "path": path,
                    "url_type": "raw",
                })
    
            # api.github.com/repos/.../contents/...
            elif "api.github.com" in url and "/repos/" in url:
                parts = url.split("/")
                repo_index = parts.index("repos")
                if len(parts) < repo_index + 3:
                    return None
    
                owner = parts[repo_index + 1]
                repo = parts[repo_index + 2]
    
                result = {"owner": owner, "repo": repo, "branch": None, "path": None, "url_type": "api"}
    
                # contents/path/to/file (may be omitted if listing a dir or repo)
                if len(parts) > repo_index + 3 and parts[repo_index + 3] == "contents":
                    raw_path = "/".join(parts[repo_index + 4 :])
                    result["path"] = strip_query_fragment(raw_path) if raw_path else None
    
                return finalize(result)
    
        except (IndexError, ValueError):
            return None
    
        return None


    def repo_exists(self, owner: str, repo: str):
        """
        Check if a repository exists and is accessible.
        Uses the GitHub API "Get a repository" endpoint as recommended for private repos.
        """
        try:
            # Use GET instead of HEAD for better private repository support
            # Following GitHub API documentation recommendations
            response = self.get(f"/repos/{owner}/{repo}")
            return response is not None
        except Exception as e:
            error_str = str(e).lower()

            # 404 means repository doesn't exist or is not accessible
            if "404" in error_str or "not found" in error_str:
                return False

            # Log other errors but return False for safety
            logger.debug(f"Error checking repository existence {owner}/{repo}: {str(e)}")
            return False

    def file_exists(self, url):
        """
        Check if a file exists in a GitHub repository using various URL formats.
        This method properly handles private repositories by first checking repository access
        as recommended in GitHub API documentation.

        Supported URL formats:
        - https://github.com/owner/repo/blob/branch/path/to/file
        - https://raw.githubusercontent.com/owner/repo/branch/path/to/file
        - https://api.github.com/repos/owner/repo/contents/path/to/file
        """
        parsed = self.parse_github_url(url)
        if not parsed:
            return False

        # Only check existence for file URLs
        if parsed["url_type"] not in ["blob", "raw", "api"]:
            return False

        owner = parsed["owner"]
        repo_name = parsed["repo"]
        branch = parsed["branch"] or "main"  # Default to main if no branch specified
        path_to_file = parsed["path"]

        if not path_to_file:
            return False

        # First, check if we have access to the repository itself
        # This is especially important for private repositories
        # Following GitHub API documentation: https://docs.github.com/en/rest/repos/repos?apiVersion=2022-11-28#get-a-repository
        if not self.repo_exists(owner, repo_name):
            logger.debug(f"Repository {owner}/{repo_name} is not accessible or doesn't exist")
            return False

        try:
            # Now check if the specific file exists within the accessible repository
            # Use GET request to the GitHub API contents endpoint
            response = self.get(f"/repos/{owner}/{repo_name}/contents/{path_to_file}?ref={branch}")

            # If we get a successful response, the file exists
            if response:
                # The response could be a file object or a list (if it's a directory)
                # For files, we expect a 'type' field with value 'file'
                if isinstance(response, dict) and response.get("type") == "file":
                    return True
                # If it's a list, it means the path points to a directory, not a file
                elif isinstance(response, list):
                    return False
                # For any other successful response format, assume file exists
                else:
                    return True
            return False

        except Exception as e:
            # Log the specific error for debugging
            logger.debug(f"Error checking file existence for {url}: {str(e)}")

            # Check for specific error types to determine if file doesn't exist vs other issues
            error_str = str(e).lower()

            # 404 errors clearly indicate the file doesn't exist (but repo is accessible)
            if "404" in error_str or "not found" in error_str:
                return False

            # 403 errors might indicate permission issues with specific files/paths
            # Since we already confirmed repo access, this is likely a file-level permission issue
            if "403" in error_str or "forbidden" in error_str:
                logger.warning(
                    f"Access forbidden for file {path_to_file} in repository {owner}/{repo_name}. "
                    f"Repository is accessible but file permissions may be restricted."
                )
                # For file-level permission issues, assume file exists but is restricted
                return True

            # 401 errors shouldn't happen here since we already validated repo access
            if "401" in error_str or "unauthorized" in error_str:
                logger.warning(
                    f"Unexpected authentication error when checking file {path_to_file} "
                    f"in accessible repository {owner}/{repo_name}."
                )
                return True

            # For any other errors (network issues, API problems, etc.)
            # we'll be conservative and assume the file exists
            logger.warning(f"Could not verify file existence for {url} due to error: {str(e)}")
            return True

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

    def get_org_repos(
        self, organization: str, type: str = "all", per_page: int = 30, sort: str = "created", direction: str = "asc"
    ) -> Generator[list[dict], None, None]:
        if per_page > 100:
            raise Exception("per_page cannot be greater than 100")

        if type not in ["all", "public", "private", "forks", "sources", "member"]:
            raise Exception("Invalid type")

        if sort not in ["created", "updated", "pushed", "full_name"]:
            raise Exception("Invalid sort")

        if direction not in ["asc", "desc"]:
            raise Exception("Invalid direction")

        page = 0
        while True:
            page += 1

            try:
                res = self.get(
                    f"/orgs/{organization}/repos?page={page}&type={type}&per_page={per_page}&sort={sort}&direction={direction}"
                )

            except Exception:
                break

            if len(res) == 0:
                break

            yield res

            if len(res) < per_page:
                break

    def get_repo_collaborators(self, owner: str, repo: str, per_page: int = 30) -> Generator[list[dict], None, None]:
        """
        Get a list of collaborators for a repository.

        Args:
            owner: The repository owner (username or organization)
            repo: The repository name
            per_page: Number of results per page (max 100)

        Returns:
            A list of collaborator objects
        """
        if per_page > 100:
            raise Exception("per_page cannot be greater than 100")

        page = 1

        while True:
            try:
                result = self.get(
                    f"/repos/{owner}/{repo}/collaborators", request_data={"per_page": per_page, "page": page}
                )

            except Exception:
                break

            if len(result) == 0:
                break

            yield result

            if len(result) < per_page:
                break

            page += 1

    def delete_org_repo(self, owner: str, repo: str):
        res = self.delete(f"/repos/{owner}/{repo}")
        return res

    def transfer_repo(self, repo: str, new_owner: str, new_name: Optional[str] = None):
        if new_name is None:
            new_name = repo
        return self.post(
            f"/repos/{self.org}/{repo}/transfer",
            request_data={"new_owner": new_owner, "new_name": new_name},
        )

    def get_repo_events(
        self,
        owner: str,
        repo: str,
        per_page: int = 30,
    ) -> Generator[list[dict], None, None]:
        if per_page > 100:
            raise Exception("per_page cannot be greater than 100")

        page = 0
        while True:
            page += 1

            try:
                res = self.get(f"/repos/{owner}/{repo}/events?page={page}&per_page={per_page}")

            except Exception:
                break

            if len(res) == 0:
                break

            yield res

            if len(res) < per_page:
                break

    def get_repository(self, owner: str, repo: str):
        """
        Get detailed repository information.
        This is useful for debugging and understanding repository access permissions.

        Returns:
            dict: Repository information or None if not accessible
        """
        try:
            return self.get(f"/repos/{owner}/{repo}")
        except Exception as e:
            logger.debug(f"Could not get repository information for {owner}/{repo}: {str(e)}")
            return None

    def create_repository(self, owner: str, repo_name: str, description: str = "", private: bool = True):
        """
        Create a new repository under the given owner (user or organization).

        Args:
            owner: The owner (username or organization) under which to create the repository
            repo_name: The name of the repository to create
            description: Optional repository description
            private: Whether the repository should be private (default: True)

        Returns:
            dict: Repository information from GitHub API
        """
        payload = {
            "name": repo_name,
            "description": description,
            "private": private,
            "auto_init": True,  # Initialize with README
        }

        logger.debug(f"Creating repository: owner={owner}, self.org={getattr(self, 'org', 'None')}")

        # Create under organization only - no fallback to user account
        logger.debug(f"Attempting to create repository under organization: {owner}")
        try:
            result = self.post(f"/orgs/{owner}/repos", request_data=payload)
            logger.debug(f"Successfully created repository under organization {owner}")
            return result
        except Exception as org_error:
            logger.error(f"Failed to create repository under organization {owner}: {str(org_error)}")
            error_msg = str(org_error).lower()

            if "not found" in error_msg:
                raise Exception(
                    f"Organization '{owner}' not found or you don't have permission to create repositories under it. Please verify the organization name and ensure your GitHub token has the necessary permissions."
                )
            elif "forbidden" in error_msg or "permission" in error_msg:
                raise Exception(
                    f"Permission denied: Your GitHub token doesn't have permission to create repositories under organization '{owner}'. Please ensure you have admin access to the organization."
                )
            else:
                raise Exception(
                    f"Failed to create repository '{repo_name}' under organization '{owner}': {str(org_error)}"
                )

    def create_file(self, owner: str, repo: str, file_path: str, content: str, message: str, branch: str = "main"):
        """
        Create a new file in a repository.

        Args:
            owner: Repository owner
            repo: Repository name
            file_path: Path where the file should be created
            content: File content (will be base64 encoded)
            message: Commit message
            branch: Branch to commit to (default: "main")

        Returns:
            dict: Response from GitHub API
        """
        import base64

        encoded_content = base64.b64encode(content.encode("utf-8")).decode("utf-8")

        payload = {"message": message, "content": encoded_content, "branch": branch}

        return self.post(f"/repos/{owner}/{repo}/contents/{file_path}", request_data=payload)
