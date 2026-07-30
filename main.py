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
    "security": "security",
    "access_and_data": "access-and-data",
    "customization": "customization",
}

load_dotenv()
TSG_ID = os.environ.get("TSG_ID")
CLIENT_ID = os.environ.get("CLIENT_ID")
SECRET_ID = os.environ.get("SECRET_ID")

OUTPUT_DIR = "output"


def create_token():
    auth_url = f"{BASE_AUTH_URL}?grant_type=client_credentials&scope:tsg_id:{TSG_ID}"

    token = requests.request(
        method="POST",
        url=auth_url,
        headers=AUTH_HEADERS,
        auth=(CLIENT_ID, SECRET_ID),
    ).json()
    HEADERS.update({"Authorization": f'Bearer {token["access_token"]}'})


def get_full_policy(policy_endpoint):
    _ = []
    url = f"{BASE_API_URL}/{policy_endpoint}"
    response = requests.get(url, headers=HEADERS).json()
    _.extend(response.get("data", []))
    return _


def get_single_policy(policy_endpoint, id):
    url = f"{BASE_API_URL}/{policy_endpoint}/rules/{id}"
    response = requests.get(url, headers=HEADERS).json()
    return response


if __name__ == "__main__":
    create_token()
    all_policy_ids = {}
    all_policy_rules = {}
    for policy_endpoint in POLICY_ENDPOINTS.values():
        _ = []
        _.extend(get_full_policy(policy_endpoint))
        all_policy_ids[policy_endpoint] = _
    ids_by_section = {
        key: [rule["id"] for rule in rules if "id" in rule]
        for key, rules in all_policy_ids.items()
    }

    for section, ids in ids_by_section.items():
        all_policy_rules[section] = []
        for id in ids:
            print(f"Getting policy for section: {section}, id: {id}")
            response = get_single_policy(section, id)
            all_policy_rules[section].append(response)
    with open(f"{OUTPUT_DIR}/all_policy_rules.json", "w", encoding="utf-8") as f:
        json.dump(all_policy_rules, f, indent=2)
