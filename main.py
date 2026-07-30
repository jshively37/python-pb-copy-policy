import argparse
import os
import json
import sys
import requests

from dotenv import load_dotenv
from pathlib import Path

BASE_AUTH_URL = "https://auth.apps.paloaltonetworks.com/auth/v1/oauth2/access_token"
BASE_API_URL = "https://api.sase.paloaltonetworks.com/seb-api/v1/policy"


HEADERS = {
    'Content-Type': 'application/json',
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
OUTPUT_FILE = "all_policy_rules.json"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Prisma Browser Policy Management Tool"
    )
    subparsers = parser.add_subparsers(dest="mode", required=True, help="Select mode")
    subparsers.add_parser(
        "export", description="Copy policy to a JSON file for later use or analysis"
    )
    subparsers.add_parser("print", description="Print policy to console")
    subparsers.add_parser("import", description="Import policy from tenant to tenant")
    return parser.parse_args()


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


def create_single_policy(policy_endpoint, rule):
    url = f"{BASE_API_URL}/{policy_endpoint}/rules"

    try:
        payload = json.dumps(rule)
        response = requests.post(url, data=payload, headers=HEADERS)
        response.raise_for_status()
        print(f"Successfully created rule: {rule.get('name', 'Unknown')} in section: {policy_endpoint}")
    except requests.exceptions.HTTPError as e:
        print(f"HTTP error occurred: {e} for rule: {rule.get('name', 'Unknown')}")



def clean_rule(rule):
    fields_to_remove = ["id", "created_at", "updated_at", "metadata", "priority"]
    for field in fields_to_remove:
        rule.pop(field, None)
    return rule

if __name__ == "__main__":
    if len(sys.argv) == 1:
        print(
            "Please provide either 'export', 'print', or 'import' when running the script.\nFor example: python main.py export"
        )
        sys.exit(1)
    args = parse_args()
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

    if args.mode == "export":
        if not os.path.exists(OUTPUT_DIR):
            print(f"Creating output directory: {OUTPUT_DIR}")
            os.makedirs(OUTPUT_DIR)
        with open(f"{OUTPUT_DIR}/{OUTPUT_FILE}", "w", encoding="utf-8") as f:
            json.dump(all_policy_rules, f, indent=2)
        print(f"Policy exported to {OUTPUT_DIR}/{OUTPUT_FILE}")
    elif args.mode == "print":
        print(json.dumps(all_policy_rules, indent=2))
    elif args.mode == "import":
        target_tsg_id = os.environ.get("TARGET_TSG_ID")
        target_client_id = os.environ.get("TARGET_CLIENT_ID")
        target_secret_id = os.environ.get("TARGET_SECRET_ID")
        if not all([target_tsg_id, target_client_id, target_secret_id]):
            print(
                "Please set TARGET_TSG_ID, TARGET_CLIENT_ID, and TARGET_SECRET_ID in the .env file for import mode."
            )
            sys.exit(1)
        for policy_endpoint, rules in all_policy_rules.items():
            for rule in rules:
                rule = clean_rule(rule)
                create_single_policy(policy_endpoint, rule)
