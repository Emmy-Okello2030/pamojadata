# kobo_connector.py — PamojaData Data Collection Module
# Pulls data directly from KoboToolbox API into PamojaData
# No more manual CSV exports — data flows automatically

import requests
import pandas as pd
import json

# KoboToolbox API base URLs
KOBO_API_URL = "https://kf.kobotoolbox.org/api/v2"
KOBO_HUMANITARIAN_URL = "https://kobo.humanitarianresponse.info/api/v2"


def get_kobo_forms(api_token, humanitarian=False):
    """
    Retrieves list of all forms/assets available in the account.
    humanitarian=True uses the UN OCHA humanitarian server.
    """
    base_url = KOBO_HUMANITARIAN_URL if humanitarian else KOBO_API_URL
    headers = {
        "Authorization": f"Token {api_token}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.get(f"{base_url}/assets/", headers=headers)
        response.raise_for_status()
        data = response.json()

        forms = []
        for asset in data.get('results', []):
            if asset.get('asset_type') == 'survey':
                forms.append({
                    'uid': asset['uid'],
                    'name': asset['name'],
                    'submissions': asset.get('deployment__submission_count', 0),
                    'date_modified': asset.get('date_modified', '')
                })
        return forms

    except requests.exceptions.RequestException as e:
        return {'error': str(e)}


def get_form_data(api_token, form_uid, humanitarian=False):
    """
    Downloads all submissions from a specific KoboToolbox form.
    Returns a pandas DataFrame.
    """
    base_url = KOBO_HUMANITARIAN_URL if humanitarian else KOBO_API_URL
    headers = {
        "Authorization": f"Token {api_token}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.get(
            f"{base_url}/assets/{form_uid}/data/",
            headers=headers,
            params={"format": "json"}
        )
        response.raise_for_status()
        data = response.json()

        submissions = data.get('results', [])
        if not submissions:
            return pd.DataFrame()

        # Flatten nested JSON responses
        df = pd.json_normalize(submissions)

        # Clean column names (KoboToolbox adds group prefixes)
        df.columns = [col.split('/')[-1] for col in df.columns]

        return df

    except requests.exceptions.RequestException as e:
        return {'error': str(e)}


def get_form_schema(api_token, form_uid, humanitarian=False):
    """
    Retrieves the form schema — useful for understanding
    what columns/questions are in the form before downloading data.
    """
    base_url = KOBO_HUMANITARIAN_URL if humanitarian else KOBO_API_URL
    headers = {
        "Authorization": f"Token {api_token}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.get(
            f"{base_url}/assets/{form_uid}/",
            headers=headers
        )
        response.raise_for_status()
        asset = response.json()

        questions = []
        for question in asset.get('content', {}).get('survey', []):
            if question.get('type') not in ['begin_group', 'end_group', 'note']:
                questions.append({
                    'name': question.get('name', ''),
                    'label': question.get('label', [''])[0] if question.get('label') else '',
                    'type': question.get('type', '')
                })
        return questions

    except requests.exceptions.RequestException as e:
        return {'error': str(e)}


def test_connection(api_token, humanitarian=False):
    """
    Tests whether the API token is valid.
    Returns True if connected, False otherwise.
    """
    base_url = KOBO_HUMANITARIAN_URL if humanitarian else KOBO_API_URL
    headers = {
        "Authorization": f"Token {api_token}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.get(f"{base_url}/assets/", headers=headers)
        return response.status_code == 200
    except Exception:
        return False


def map_kobo_to_indicators(df, mapping):
    """
    Maps KoboToolbox form columns to PamojaData
    standard indicator structure.
    """
    mapped_df = pd.DataFrame()

    try:
        mapped_df['Indicator Name'] = df[mapping.get('indicator_name', '')]
        mapped_df['Sector'] = df[mapping.get('sector', '')]
        mapped_df['Target'] = pd.to_numeric(df[mapping.get('target', '')], errors='coerce').fillna(0)
        mapped_df['Achieved'] = pd.to_numeric(df[mapping.get('achieved', '')], errors='coerce').fillna(0)

        if mapping.get('period') and mapping['period'] in df.columns:
            mapped_df['Reporting Period'] = df[mapping['period']]

        if mapping.get('location') and mapping['location'] in df.columns:
            mapped_df['Location'] = df[mapping['location']]

        if mapping.get('notes') and mapping['notes'] in df.columns:
            mapped_df['Notes'] = df[mapping['notes']]

        return mapped_df

    except KeyError as e:
        return {'error': f"Column not found: {str(e)}"}