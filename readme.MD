# Overview
This Python script walks through programmatically retrieving the Prisma Browser Policy (security, customization, and policy sections) and either writes it to a file or copies it to another tenant.

## Disclaimer

This project is provided as-is, without warranty of any kind, express or implied. No support, maintenance, bug fixes, or updates are offered or implied.
By using this software, you agree that:

* You assume all risk and liability arising from its use
* The author(s) are not responsible for any damages, data loss, system failures, or other consequences resulting from use or misuse of this code
* No support requests, issues, or pull requests will be acknowledged or addressed

Use at your own discretion.

## Limitations:
* Right now just copies to a file.
* Phase 2 will be copy to another tenant.

## Creating a service account in Prisma Access

You will need to create a service account in Prisma Access to generate the access token.

The Client ID, Secret ID, and TSG ID will be saved in the .env file.

To create a service account: https://pan.dev/sase/docs/service-accounts/


## Installing and running

Clone down this repo and cd into the directory.

Create a Python virtual environment: python -m venv venv

Activate the virtual environment: \
Windows: .\venv\Scripts\activate \
OSX: source venv/bin/activate \

Install the dependencies using `pip install -r requirements.txt`

Copy `env.example` to `.env` and populate your variables in this file generated while creating the service account. The .env is included in the .gitignore to ensure it does not accidentally get checked into a git repo.

If you wish to use `import` CLI argument you will need to populate the `TARGET_TSG_ID`, `TARGET_CLIENT_ID`, and `TARGET_SECRET_ID` fields.

Run: `python main.py` and pass in the approriate CLI argument (You can use `python main.py --help` to see all available options): \
`print`: Print all the polices to the screen.\
`export`: Save the policies in a JSON file in the location defined by: `OUTPUT_DIR` and `OUTPUT_FILE`\
`import`: Copy the policy from one tenant to another tenant. Make sure you've defined both sets of credentials in `.env`.\

For example to print the policy to the screen you would enter in `python main.py print`
