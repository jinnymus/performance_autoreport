import os
import requests
import re
from settings import settings
import json
from typing import Optional, List

from web.model import ApplicationsModel


def search_parameter(parameters, name):
    for param in parameters:
        if param['name'].lower() == name.lower():
            return param['value']


class ArgoAdapter:
    def __init__(self, argo_url: str | None = None, username: str = None, password: str = None, token: str = None):
        self.__argo_host = settings.argo_host
        self.__argo_login = settings.argo_login
        self.__argo_password = settings.argo_password
        self.__argo_token = None
        self.keycloak_url = os.environ.get(
            "KEYCLOAK_AUTH_URL",
            "https://sso.example.com/auth/realms/example/login-actions/authenticate",
        )
        self.argo_url = argo_url or os.environ.get("ARGO_URL") or f"https://{self.__argo_host}"
        self.client_id = os.environ.get("ARGO_OAUTH_CLIENT_ID", "argocd")
        self.token = token
        self.username = username
        self.password = password
        self.headers = {
            'Authorization': f'Bearer {self.token}'
        }

    def update_token(self):
        response = requests.post(f"https://{self.__argo_host}/api/v1/session", verify=False,
                                 json={"username": self.__argo_login, "password": self.__argo_password})
        print(f"[update_token] response: {response.text}")
        # self.__argo_token = requests.post(f"https://{self.__argo_host}/api/v1/session", verify=False, json={"username": self.__argo_login, "password": self.__argo_password}).json()['token']
        self.__argo_token = response.json()['token']


    def get_app_versions(self, service_pods: List[ApplicationsModel]):
        versions = dict()
        for pod in service_pods:
            application = pod.application
            env = pod.env
            namespace = pod.namespace
            resource = pod.resource
            kind = pod.kind
            # application = "host-external-load-host-web-ui"
            # namespace = "host-external-load"
            # resource = "host-web-ui"
            # kind = "Deployment"

            deployment_info_url = (
                f"https://{self.__argo_host}/api/v1/applications/{application}/resource?"
                f"name={resource}&appNamespace=argocd&namespace={namespace}&resourceName={resource}"
                f"&version=v1&kind={kind}&group=apps"
            )
            print(f"[get_deployment_info] deployment_info_url: {deployment_info_url}")

            response_data = requests.get(f"{deployment_info_url}", verify=False,
                                         headers={"Authorization": f"Bearer {self.token}"}).json()
            #print(f"[get_deployment_info] response_data: {response_data}")
            manifest = json.loads(response_data['manifest'])
            version = manifest['metadata']['labels']['helm.sh/chart']
            replicas = manifest['spec']['replicas']
            image = str(manifest['spec']['template']['spec']['containers'][0]['image'])
            resources_limits_cpu = str(manifest['spec']['template']['spec']['containers'][0]['resources']['limits']["cpu"])
            resources_limits_memory = str(manifest['spec']['template']['spec']['containers'][0]['resources']['limits']["memory"])
            resources_requests_cpu = str(manifest['spec']['template']['spec']['containers'][0]['resources']['requests']["cpu"])
            resources_requests_memory = str(manifest['spec']['template']['spec']['containers'][0]['resources']['requests']["memory"])
            envs = manifest['spec']['template']['spec']['containers'][0]['env']
            print(f"[get_deployment_info] envs: {envs}")
            envs_dict = dict()
            for item in envs:
                if ("value" in item):
                    envs_dict[item["name"]]=item["value"]
            print(f"[get_deployment_info] version: {version}")
            print(f"[get_deployment_info] replicas: {replicas}")
            print(f"[get_deployment_info] image: {image}")
            print(f"[get_deployment_info] resources_limits_cpu: {resources_limits_cpu}")
            print(f"[get_deployment_info] resources_limits_memory: {resources_limits_memory}")
            print(f"[get_deployment_info] resources_requests_cpu: {resources_requests_cpu}")
            print(f"[get_deployment_info] resources_requests_memory: {resources_requests_memory}")
            print(f"[get_deployment_info] envs_dict: {envs_dict}")
            versions[env] = version
        return versions


    def get_deployment_info(self, service_pods: List[ApplicationsModel]):
        table_value = []
        table_column = [
            'Application',
            'resources.requests.cpu',
            'resources.requests.memory',
            'resources.limits.cpu',
            'resources.limits.memory',
            'replicaCount',
            'env',
            'Version'
        ]

        for pod in service_pods:
            application = pod.application
            namespace = pod.namespace
            resource = pod.resource
            kind = pod.kind
            # application = "host-external-load-host-web-ui"
            # namespace = "host-external-load"
            # resource = "host-web-ui"
            # kind = "Deployment"

            deployment_info_url = (
                f"https://{self.__argo_host}/api/v1/applications/{application}/resource"
                f"?name={resource}&appNamespace=argocd&namespace={namespace}"
                f"&resourceName={resource}&version=v1&kind={kind}&group=apps"
            )
            print(f"[get_deployment_info] deployment_info_url: {deployment_info_url}")

            response_data = requests.get(deployment_info_url, verify=False,
                                         headers={"Authorization": f"Bearer {self.token}"}).json()
            #print(f"[get_deployment_info] response_data: {response_data}")
            manifest = json.loads(response_data['manifest'])
            version = manifest['metadata']['labels']['helm.sh/chart']
            replicas = manifest['spec']['replicas']
            image = str(manifest['spec']['template']['spec']['containers'][0]['image'])
            resources_limits_cpu = str(manifest['spec']['template']['spec']['containers'][0]['resources']['limits']["cpu"])
            resources_limits_memory = str(manifest['spec']['template']['spec']['containers'][0]['resources']['limits']["memory"])
            resources_requests_cpu = str(manifest['spec']['template']['spec']['containers'][0]['resources']['requests']["cpu"])
            resources_requests_memory = str(manifest['spec']['template']['spec']['containers'][0]['resources']['requests']["memory"])
            envs = manifest['spec']['template']['spec']['containers'][0]['env']
            print(f"[get_deployment_info] envs: {envs}")
            envs_dict = dict()
            for item in envs:
                if ("value" in item):
                    envs_dict[item["name"]]=item["value"]
            print(f"[get_deployment_info] version: {version}")
            print(f"[get_deployment_info] replicas: {replicas}")
            print(f"[get_deployment_info] image: {image}")
            print(f"[get_deployment_info] resources_limits_cpu: {resources_limits_cpu}")
            print(f"[get_deployment_info] resources_limits_memory: {resources_limits_memory}")
            print(f"[get_deployment_info] resources_requests_cpu: {resources_requests_cpu}")
            print(f"[get_deployment_info] resources_requests_memory: {resources_requests_memory}")
            print(f"[get_deployment_info] envs_dict: {envs_dict}")
            table_value.append([
                    application,
                    resources_requests_cpu,
                    resources_requests_memory,
                    resources_limits_cpu,
                    resources_limits_memory,
                    replicas,
                    envs_dict,
                    version
                ])
        return table_value, table_column

    def get_applications_info(self, service_pods: list):
        table_value = []
        table_column = [
            'Container',
            'resources.requests.cpu',
            'resources.requests.memory',
            'resources.limits.cpu',
            'resources.limits.memory',
            'replicaCount',
            'logLevel',
            'Version'
        ]
        for pod in service_pods:
            response_data = requests.get(
                f"https://{self.__argo_host}/api/v1/applications/{pod}",
                verify=False,
                headers={"Authorization": f"Bearer {self.__argo_token}"},
            ).json()
            version = response_data['status']['operationState']['syncResult']['revision']
            parameter = response_data['spec']['source']['helm']['parameters']
            level_default = search_parameter(parameter, 'env.OPN_Serilog__MinimumLevel__Default')
            table_value.append([
                pod,
                search_parameter(parameter, 'resources.requests.cpu'),
                search_parameter(parameter, 'resources.requests.memory'),
                search_parameter(parameter, 'resources.limits.cpu'),
                search_parameter(parameter, 'resources.limits.memory'),
                search_parameter(parameter, 'replicaCount'),
                level_default if level_default else 'Information',
                version
            ])
        return table_value, table_column
