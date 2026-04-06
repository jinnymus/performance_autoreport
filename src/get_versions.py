import os
from typing import List
import logging
import json
from clients.vault_client import VaultClient
from clients.argocd import ArgoAdapter
from web.model import ArgoBase, VaultBase
from web.model import ApplicationsModel
import argparse

logger = logging.getLogger('root')
logging.basicConfig(
    format='%(asctime)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    level=logging.DEBUG,
    force=True
)

parser = argparse.ArgumentParser(prog='yacloud')
parser.add_argument('--argo_url', help='argo_url')
parser.add_argument('--argo_token', help='argo_token')
parser.add_argument('--vault_token', help='vault_token')
parser.add_argument('--vault_application', help='vault_application')
args = parser.parse_args()

argo_url = os.environ.get("ARGO_URL", "https://argocd.example.com")
# Example layout; override via your CI or edit for your Argo CD applications.
applications = [
    {
        "application": "demo-web-ui",
        "env": "UI_VERSION",
        "namespace": "default",
        "resource": "web-ui",
        "kind": "Deployment",
    },
    {
        "application": "demo-web-api",
        "env": "CMS_VERSION",
        "namespace": "default",
        "resource": "web-api",
        "kind": "Deployment",
    },
]
def get_app_versions(argo_url: str, argo_token: str, applications: List[ApplicationsModel]):
    argo = ArgoAdapter(argo_url = argo_url, token = argo_token)
    #value, column = argo.get_applications_info([app.name for app in applications])
    versions = argo.get_app_versions(applications)
    return versions

def get_db_version(vault_token: str, vault_applications: list):
    vault_client = VaultClient(token = vault_token)
    #value, column = argo.get_applications_info([app.name for app in applications])
    data = dict()
    for app in vault_applications:
        vault_data = json.loads(vault_client.get_secret_json(app))
        logger.debug(f"[get_db_version] vault_data: {vault_data}")
        dbname = vault_data['data']['data']['OrchardCore']['Default']['ConnectionString'].split(';')[4].split('=')[1]
        # OrchardCore.Default.ConnectionString
        # Database
        logger.debug(f"[get_db_version] dbname: {dbname}")
        data['DB_VERSION'] = dbname
    return data

if __name__ == "__main__":
    result = dict()

    # Prefer explicit pipeline env vars; otherwise resolve from Argo / Vault.
    ui_version = os.environ.get('UI_VERSION', '').strip()
    cms_version = os.environ.get('CMS_VERSION', '').strip()
    db_version_param = os.environ.get('DB_VERSION', '').strip()
    
    if ui_version and cms_version and db_version_param:
        logger.info(f"[__main__] Using versions from pipeline params: UI={ui_version}, CMS={cms_version}, DB={db_version_param}")
        result = {
            'UI_VERSION': ui_version,
            'CMS_VERSION': cms_version,
            'DB_VERSION': db_version_param
        }
    else:
        logger.info("[__main__] Getting versions from Argo/Vault")
        applications_models: List[ApplicationsModel] = [ApplicationsModel(**app) for app in applications]
        versions = get_app_versions(
            argo_url=args.argo_url or argo_url,
            argo_token=args.argo_token,
            applications=applications_models,
        )
        logger.debug(f"[__main__] versions: {versions}")
        db_version = get_db_version(vault_token=args.vault_token, vault_applications=[args.vault_application])
        logger.debug(f"[__main__] db_version: {db_version}")
        result = versions | db_version
        
        # Allow partial overrides from the environment
        if ui_version:
            result['UI_VERSION'] = ui_version
        if cms_version:
            result['CMS_VERSION'] = cms_version
        if db_version_param:
            result['DB_VERSION'] = db_version_param
    
    logger.debug(f"[__main__] result: {result}")
    print(result)
