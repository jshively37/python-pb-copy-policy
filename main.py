import os
import json
import requests

from dotenv import load_dotenv

BASE_AUTH_URL = "https://auth.apps.paloaltonetworks.com/auth/v1/oauth2/access_token"
BASE_API_URL = "https://api.sase.paloaltonetworks.com/seb-api/v1/policy"


HEADERS = {
    "Accept": "application/json",
}

AUTH_HEADERS = {
    "Content-Type": "application/x-www-form-urlencoded",
    "Accept": "application/json",
}

POLICY_ENDPOINTS = {
    "security": "/security",
    "access_and_data": "/access-and-data",
    "customization": "/customization",
}

load_dotenv()
TSG_ID = os.environ.get("TSG_ID")
CLIENT_ID = os.environ.get("CLIENT_ID")
SECRET_ID = os.environ.get("SECRET_ID")

OUTPUT_DIR = 'output'


def create_token():
    auth_url = f"{BASE_AUTH_URL}?grant_type=client_credentials&scope:tsg_id:{TSG_ID}"

    token = requests.request(
        method="POST",
        url=auth_url,
        headers=AUTH_HEADERS,
        auth=(CLIENT_ID, SECRET_ID),
    ).json()
    HEADERS.update({"Authorization": f'Bearer {token["access_token"]}'})


def get_all_pb_policy():
    url = f"{BASE_API_URL}/seb-api/v1/policy/access-and-data"
    response = requests.request(
        method="GET",
        url=url,
        headers=HEADERS
    )
    return response.json()


def get_single_pb_policy(id):
    url = f"{BASE_API_URL}/seb-api/v1/policy/access-and-data/rules/{id}"
    response = requests.request(
        method="GET",
        url=url,
        headers=HEADERS
    )
    return response.json()

if __name__ == "__main__":
    create_token()
    full_policy = []
    policies = get_all_pb_policy()
    ids = [item['id'] for item in policies.get('data', [])]
    for id in ids:
        response = get_single_pb_policy(id)
        full_policy.append(response)
    with open(f"{OUTPUT_DIR}/full_policy.json", "w") as f:
        json.dump(full_policy, f, indent=4)
