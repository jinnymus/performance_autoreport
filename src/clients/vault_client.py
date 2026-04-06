import logging
import os
import requests
import json
import re


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

class VaultClient:
    def __init__(self, vault_url="https://vault.example.com", token=None):
        logger.debug("[VaultClient] init")
        self.vault_url = vault_url
        self.token = token
    
    
    def get_vault_secret(self, path):
        """
        Read a secret path from Vault and return parsed JSON.

        Args:
            path: Secret path (e.g. ``secret/data/myapp/config``).

        Returns:
            Parsed JSON ``dict``, or ``None`` on HTTP errors.
        """
        vault_token = self.token or os.getenv("VAULT_TOKEN")
        if not vault_token:
            raise ValueError("Vault token is not set (constructor or VAULT_TOKEN env)")

        headers = {
            "X-Vault-Token": vault_token,
            "Content-Type": "application/json"
        }
    
        api_path = f"{self.vault_url}/v1/{path}"
    
        try:
            response = requests.get(api_path, headers=headers, verify=False)
            response.raise_for_status()
    
            return response.json()
    
        except requests.exceptions.RequestException as e:
            logger.debug(f"Vault request failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.debug(f"HTTP status: {e.response.status_code}")
                logger.debug(f"Response body: {e.response.text}")
            return None
    
    
    def sanitize_secrets(self, data,
                         sensitive_keys=["password", "AuthorizationToken", "SecretKey"],
                         mask_char="*"):
        """
        Recursively mask sensitive keys in JSON-like structures.
        """
        if isinstance(data, dict):
            result = {}
            for key, value in data.items():
                if key.lower() in [k.lower() for k in sensitive_keys]:
                    result[key] = "****"
                elif isinstance(value, (dict, list)):
                    result[key] = self.sanitize_secrets(value, sensitive_keys, mask_char)
                else:
                    if isinstance(value, str):
                        value = re.sub(r'Password=[^;]+;', r'Password=****;', value, flags=re.IGNORECASE)
                    result[key] = value
            return result
    
        elif isinstance(data, list):
            return [self.sanitize_secrets(item, sensitive_keys, mask_char) for item in data]
    
        else:
            return data

    def get_secret_json(self, secret_path):
        raw_data = self.get_vault_secret(path=secret_path)
        sanitized_data = self.sanitize_secrets(raw_data)
        result = json.dumps(sanitized_data, indent=4, ensure_ascii=False)
        return result

