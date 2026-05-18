# hdx_connector.py — PamojaData HDX Integration Module
# Connects to the Humanitarian Data Exchange (HDX) API
# Pulls live humanitarian datasets directly into PamojaData
# Reference: https://hdx.rwlabs.org/api/3

import requests
import pandas as pd

# HDX API base URL
HDX_API_URL = "https://data.humdata.org/api/3"

# Curated list of high-value humanitarian datasets
FEATURED_DATASETS = {
    "UNHCR Refugee Population": "unhcr-population-data",
    "OCHA Food Security": "fts-requirements-and-funding-data",
    "WHO Disease Outbreaks": "who-disease-outbreak-news",
    "World Bank Poverty Data": "world-bank-indicators-of-interest-to-the-food-security-analysis",
    "ACLED Conflict Data": "acled-conflict-data-for-africa",
    "FEWS NET Food Insecurity": "fews-net-food-security",
    "IOM Displacement Tracking": "iom-displacement-tracking-matrix",
    "WFP Food Prices": "wfp-food-prices"
}

# Country codes for filtering
AFRICAN_COUNTRIES = {
    "Kenya": "KEN", "Uganda": "UGA", "Ethiopia": "ETH",
    "Somalia": "SOM", "Tanzania": "TZA", "Rwanda": "RWA",
    "South Sudan": "SSD", "DRC": "COD", "Nigeria": "NGA",
    "Ghana": "GHA", "Mozambique": "MOZ", "Zimbabwe": "ZWE",
    "Malawi": "MWI", "Zambia": "ZMB", "Sudan": "SDN",
    "Chad": "TCD", "Niger": "NER", "Mali": "MLI",
    "Burkina Faso": "BFA", "Cameroon": "CMR"
}


def search_datasets(query, rows=10, country_code=None):
    """
    Searches HDX for datasets matching a query.
    Optionally filters by country code.
    """
    params = {
        "q": query,
        "rows": rows,
        "sort": "score desc",
        "fq": f"groups:{country_code.lower()}" if country_code else ""
    }

    try:
        response = requests.get(
            f"{HDX_API_URL}/action/package_search",
            params=params,
            timeout=10
        )
        response.raise_for_status()
        data = response.json()

        if not data.get('success'):
            return []

        datasets = []
        for pkg in data['result']['results']:
            datasets.append({
                'id': pkg.get('id', ''),
                'name': pkg.get('name', ''),
                'title': pkg.get('title', ''),
                'organization': pkg.get('organization', {}).get('title', ''),
                'last_modified': pkg.get('metadata_modified', ''),
                'num_resources': len(pkg.get('resources', [])),
                'resources': pkg.get('resources', [])
            })
        return datasets

    except requests.exceptions.ConnectionError:
        return {'error': 'Connection failed. Check your internet connection.'}
    except requests.exceptions.Timeout:
        return {'error': 'Request timed out. HDX may be slow — try again.'}
    except Exception as e:
        return {'error': str(e)}


def get_dataset(dataset_name):
    """
    Retrieves full details of a specific dataset by name.
    """
    try:
        response = requests.get(
            f"{HDX_API_URL}/action/package_show",
            params={"id": dataset_name},
            timeout=10
        )
        response.raise_for_status()
        data = response.json()

        if not data.get('success'):
            return {'error': 'Dataset not found.'}

        return data['result']

    except Exception as e:
        return {'error': str(e)}


def download_resource(resource_url, file_format='csv'):
    """
    Downloads a dataset resource and returns it as a DataFrame.
    Supports CSV and Excel formats.
    """
    try:
        response = requests.get(resource_url, timeout=30)
        response.raise_for_status()

        from io import StringIO, BytesIO

        if file_format.lower() == 'csv':
            df = pd.read_csv(StringIO(response.text), low_memory=False)
        elif file_format.lower() in ['xlsx', 'xls']:
            df = pd.read_excel(BytesIO(response.content))
        else:
            # Try CSV first, then Excel
            try:
                df = pd.read_csv(StringIO(response.text), low_memory=False)
            except Exception:
                df = pd.read_excel(BytesIO(response.content))

        return df

    except requests.exceptions.Timeout:
        return {'error': 'Download timed out. File may be too large.'}
    except Exception as e:
        return {'error': f'Download failed: {str(e)}'}


def get_resource_list(dataset_name):
    """
    Gets the list of downloadable files for a dataset.
    """
    dataset = get_dataset(dataset_name)
    if not isinstance(dataset, dict):
        return {'error': 'Invalid dataset response.'}
    if 'error' in dataset:
        return dataset

    resources = []
    resource_list = dataset.get('resources', [])
    if not isinstance(resource_list, list):
        return resources

    for r in resource_list:
        if not isinstance(r, dict):
            continue
        resources.append({
            'id': r.get('id', ''),
            'name': r.get('name', ''),
            'format': r.get('format', ''),
            'url': r.get('url', ''),
            'size': r.get('size', 0),
            'last_modified': r.get('last_modified', '')
        })
    return resources


def get_country_datasets(country_code, topic=None):
    """
    Gets all datasets for a specific country.
    Optionally filters by topic (food, health, displacement etc).
    """
    query = topic if topic else "*"
    return search_datasets(query, rows=20, country_code=country_code)


def format_dataset_for_analysis(df, indicator_col, value_col,
                                  sector, period_col=None):
    """
    Formats an HDX dataset into PamojaData indicator structure.
    Makes it compatible with the analysis engine.
    """
    formatted = pd.DataFrame()

    try:
        formatted['Indicator Name'] = df[indicator_col].astype(str)
        formatted['Sector'] = sector
        formatted['Target'] = 0
        formatted['Achieved'] = pd.to_numeric(
            df[value_col], errors='coerce'
        ).fillna(0)

        if period_col and period_col in df.columns:
            formatted['Reporting Period'] = df[period_col].astype(str)
        else:
            formatted['Reporting Period'] = 'HDX Import'

        formatted['Data Source'] = 'HDX'
        return formatted

    except KeyError as e:
        return {'error': f'Column not found: {str(e)}'}


def get_hdx_stats():
    """
    Gets basic HDX platform statistics.
    """
    try:
        response = requests.get(
            f"{HDX_API_URL}/action/package_search",
            params={"q": "*", "rows": 0},
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        return {
            'total_datasets': data['result']['count'],
            'status': 'Connected'
        }
    except Exception:
        return {
            'total_datasets': 'Unknown',
            'status': 'Disconnected'
        }