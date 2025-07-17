import os
import json
import pandas as pd
import gspread
import requests
from dotenv import load_dotenv
from oauth2client.service_account import ServiceAccountCredentials

# Load environment variables from .env file (locally)
load_dotenv()

# GitHub credentials
token = os.getenv('GH_TOKEN')
owner = os.getenv('OWNER')
repo = os.getenv('GH_REPO')
planilha = os.getenv('LINK_PLANILHA')

# Google service account JSON from GitHub Secrets or environment variable
service_account_json = os.getenv('GCP_SERVICE_ACCOUNT_KEY')

# Validate required environment variables
if not token or not owner or not repo or not planilha or not service_account_json:
    print("Make sure the environment variables GH_TOKEN, OWNER, GH_REPO, LINK_PLANILHA, and GCP_SERVICE_ACCOUNT_KEY are correctly set.")
    exit()

# Parse the service account JSON string into a dict
try:
    creds_dict = json.loads(service_account_json)
except json.JSONDecodeError as e:
    print(f"Failed to parse GCP_SERVICE_ACCOUNT_KEY JSON: {e}")
    exit()

# Authorize Google Sheets access
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
try:
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
except Exception as e:
    print(f"Failed to authorize Google Sheets client: {e}")
    exit()

# Open the spreadsheet
try:
    sheet = client.open_by_url(planilha).sheet1
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    print(df)
except Exception as e:
    print(f"Error reading the Google Sheets data: {e}")
    exit()

# Validate required columns
expected_columns = {'username'}
if not expected_columns.issubset(df.columns):
    print(f"The Google Sheets spreadsheet must contain the columns: {expected_columns}")
    exit()

# Iterate through the rows and send GitHub invitations
for index, row in df.iterrows():
    username = row['username']
    permission = 'pull'  # Can be 'pull', 'push', or 'admin'

    if pd.isna(username):
        print(f"Row {index + 1} is missing username. Skipping.")
        continue

    url = f'https://api.github.com/repos/{owner}/{repo}/collaborators/{username}'
    headers = {
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github+json'
    }
    data = {
        'permission': permission
    }

    response = requests.put(url, headers=headers, json=data)

    if response.status_code == 201:
        print(f"Invitation sent successfully to {username}!")
    elif response.status_code == 204:
        print(f"{username} is already a collaborator or invitation already sent.")
    else:
        print(f"Failed to invite {username}: {response.status_code}")
        try:
            print(response.json())
        except Exception:
            print("No JSON response.")
