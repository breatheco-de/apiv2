from breathecode.services.slack import client

token = "12345"
api = client.Slack(token)
data = api.get("users.list", {"limit": 300})

members = data["members"]
while (
    "response_metadata" in data
    and "next_cursor" in data["response_metadata"]
    and data["response_metadata"]["next_cursor"] != ""
):
    print("Next cursor: ", data["response_metadata"]["next_cursor"])
    data = api.get("users.list", {"limit": 300, "cursor": data["response_metadata"]["next_cursor"]})
    members = members + data["members"]

print(len(members))

from breathecode.services.slack import client

api = client.Slack(token)
data = api.get("users.list")
print(len(data["members"]))
