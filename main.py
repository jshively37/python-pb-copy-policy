import argparse
import json
import os
import sys
from pathlib import Path
import requests
from dotenv import load_dotenv

BASE_AUTH_URL = "https://auth.apps.paloaltonetworks.com/auth/v1/oauth2/access_token"
BASE_API_URL = "https://api.sase.paloaltonetworks.com/seb-api/v1/policy"

POLICY_ENDPOINTS = {
    "security": "security",
    "access_and_data": "access-and-data",
    "customization": "customization",
}

OUTPUT_DIR = Path("output")
OUTPUT_FILE = OUTPUT_DIR / "all_policy_rules.json"

FIELDS_TO_CLEAN = {"id", "created_at", "updated_at", "metadata", "priority"}


class PrismaPolicyClient:
    """Encapsulates API operations for a specific tenant session."""

    def __init__(self, tsg_id: str, client_id: str, secret_id: str):
        self.tsg_id = tsg_id
        self.session = requests.Session()
        self.session.headers.update(
            {"Content-Type": "application/json", "Accept": "application/json"}
        )
        self._authenticate(client_id, secret_id)

    def _authenticate(self, client_id: str, secret_id: str) -> None:
        auth_url = f"{BASE_AUTH_URL}?grant_type=client_credentials&scope:tsg_id:{self.tsg_id}"
        auth_headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        }

        response = requests.post(
            auth_url,
            headers=auth_headers,
            auth=(client_id, secret_id),
        )
        response.raise_for_status()

        token = response.json().get("access_token")
        if not token:
            raise KeyError("Access token was missing from authentication response.")

        self.session.headers.update({"Authorization": f"Bearer {token}"})

    def get_rules_summary(self, endpoint: str) -> list[dict]:
        """Fetch the high-level list of rules (with IDs) for a policy section."""
        url = f"{BASE_API_URL}/{endpoint}"
        response = self.session.get(url)
        response.raise_for_status()
        return response.json().get("data", [])

    def get_single_rule(self, endpoint: str, rule_id: str) -> dict:
        """Fetch the full detail for a single policy rule by ID."""
        url = f"{BASE_API_URL}/{endpoint}/rules/{rule_id}"
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()

    def create_single_rule(self, endpoint: str, rule: dict) -> None:
        """Create a single policy rule."""
        url = f"{BASE_API_URL}/{endpoint}/rules"
        rule_name = rule.get("name", "Unknown")

        try:
            response = self.session.post(url, json=rule)
            response.raise_for_status()
            print(f"Successfully created rule: '{rule_name}' in section: {endpoint}")
        except requests.exceptions.HTTPError as e:
            print(f"HTTP error creating rule '{rule_name}' in {endpoint}: {e}")

    def fetch_all_detailed_policies(self) -> dict[str, list[dict]]:
        """Utility to fetch all detailed rules across all configured endpoints."""
        all_rules = {}
        for section in POLICY_ENDPOINTS.values():
            summaries = self.get_rules_summary(section)
            all_rules[section] = []

            for rule in summaries:
                rule_id = rule.get("id")
                if not rule_id:
                    continue
                print(f"Getting policy for section: {section}, id: {rule_id}")
                detailed_rule = self.get_single_rule(section, rule_id)
                all_rules[section].append(detailed_rule)

        return all_rules


def parse_args():
    parser = argparse.ArgumentParser(
        description="Prisma Browser Policy Management Tool"
    )
    parser.add_argument(
        "mode",
        choices=["export", "print", "import"],
        help="Mode of operation: export to file, print to console, or import to another tenant.",
    )
    return parser.parse_args()


def clean_rule(rule: dict) -> dict:
    """Remove system metadata fields from a rule dictionary."""
    return {k: v for k, v in rule.items() if k not in FIELDS_TO_CLEAN}


def get_env_credentials(prefix: str = "") -> tuple[str, str, str]:
    """Retrieve credential tuple from environment with optional prefix."""
    tsg_id = os.environ.get(f"{prefix}TSG_ID")
    client_id = os.environ.get(f"{prefix}CLIENT_ID")
    secret_id = os.environ.get(f"{prefix}SECRET_ID")

    if not all([tsg_id, client_id, secret_id]):
        missing = [
            f"{prefix}{name}"
            for name, val in [("TSG_ID", tsg_id), ("CLIENT_ID", client_id), ("SECRET_ID", secret_id)]
            if not val
        ]
        print(f"Error: Missing environment variables: {', '.join(missing)}")
        sys.exit(1)

    return tsg_id, client_id, secret_id


def main():
    load_dotenv()
    args = parse_args()

    # Setup source client
    src_tsg, src_client_id, src_secret = get_env_credentials()
    src_client = PrismaPolicyClient(src_tsg, src_client_id, src_secret)

    # Fetch full policies from source tenant
    source_policies = src_client.fetch_all_detailed_policies()

    if args.mode == "export":
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(source_policies, f, indent=2)
        print(f"Policy successfully exported to {OUTPUT_FILE}")

    elif args.mode == "print":
        print(json.dumps(source_policies, indent=2))

    elif args.mode == "import":
        # Setup target tenant client
        tgt_tsg, tgt_client_id, tgt_secret = get_env_credentials(prefix="TARGET_")
        tgt_client = PrismaPolicyClient(tgt_tsg, tgt_client_id, tgt_secret)

        # Collect existing rule names in target tenant for constant-time existence checks
        target_rule_names = {
            rule["name"]
            for endpoint in POLICY_ENDPOINTS.values()
            for rule in tgt_client.get_rules_summary(endpoint)
            if "name" in rule
        }


        # Process and import missing rules
        for endpoint, rules in source_policies.items():
            for raw_rule in rules:
                rule = clean_rule(raw_rule)
                rule_name = rule.get("name")

                if rule_name and rule_name not in target_rule_names:
                    print(f"Creating rule: '{rule_name}' in section: {endpoint}")
                    tgt_client.create_single_rule(endpoint, rule)
                else:
                    print(
                        f"Skipping rule: '{rule_name}' in section: {endpoint} (Already exists in target)"
                    )


if __name__ == "__main__":
    main()
