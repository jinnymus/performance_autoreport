import logging
from typing import Optional, List

import pandas as pd

from clients.awr import AWRReports
from clients.argocd import ArgoAdapter
from confluence.macros import *
from confluence.tag import element, tag, BaseElementABC

# Load test environment description block
from web.model import ApplicationsModel

from web.model import ArgoBase

from clients.vault_client import VaultClient

from web.model import VaultBase

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)


def block_load_plan(load_plan: list[list[int]]) -> element:
    column = ['Load step, %', 'Ramp-up, min', 'Duration, min']
    value = [(step[3], step[0], step[1]) for step in load_plan]
    return element(pd.DataFrame(value, columns=column).to_html(index=False))


def block_purpose(test_desc: str) -> tuple[BaseElementABC, ...]:
    return (
        tag('h1')('Test objectives'),
        tag('p')(
            'Describe the problem this test addresses, the test type, and why it is being run.'
        ),
        tag('p')(test_desc),
    )


def block_conclusion() -> tuple[BaseElementABC, ...]:
    return (
        tag('h1')('Conclusion'),
        tag('p')(
            """Depending on the test type and goals, summarize results and answer the test objectives.
            Include business and infrastructure metrics at the highest load step and at the 100% load step."""
        ),
        tag('p')(
            """For maximum-performance tests across all operations, state the same for a subset of operations
            if the run used background load or scoped operations only:"""
        ),
        tag('ul')(
            tag('li')(
                'Performance headroom: load at the 100% step and at the last stable step for all operations.'
            ),
            tag('li')(
                """Business metrics: response times per operation in a table by step, or at least at 100% and
                last stable step if a full table is not feasible."""
            ),
            tag('li')(
                'Whether SLA was exceeded, on which step, and load as a multiple (×N) of the profile.'
            ),
        ),
        tag('p')('For reliability (stability) tests, include:'),
        tag('ul')(
            tag('li')(
                'Infrastructure utilization at the start, middle, and end of the test for trend comparison.'
            ),
            tag('li')(
                'Business metric utilization (response times) at the start, middle, and end for comparison.'
            ),
        ),
        tag('h2')('Defects'),
        tag('p')('Omit this section if there are no defects; each defect should have a tracked ticket.'),
        tag('h2')('Recommendations'),
        tag('p')('Omit this section if there are no recommendations.'),
    )


def block_mnt(load_plan: list[list[int]], jmx_path: str) -> tuple[BaseElementABC, ...]:
    return (
        tag('h1')('Methodology summary'),
        tag('h2')('Test constraints'),
        tag('h3')('Business metric requirements'),
        tag('ul')(
            tag('li')('P90 response time ≤ XX s per minute for operation XXXXXX'),
            tag('li')('No more than 5% non-functional errors.'),
            tag('li')('Deviation from planned load ≤ 10%.'),
        ),
        tag('h3')('Infrastructure metric requirements'),
        tag('ul')(
            tag('li')('Service uses at most 75% CPU and RAM on containers and pods')
        ),
        tag('h2')('Load profile'),
        tag('p')(f'Load script: {jmx_path}'),
        tag('h2')('Load plan'),
        block_load_plan(load_plan),
        tag('h2')('Deviations from methodology'),
        tag('ul')(
            tag('li')('Testing runs on a single cluster / availability zone'),
            tag('li')('Test database size and compute resources may not match production'),
        ),
    )


def block_config_ppo(argo_base: ArgoBase, vault_base: VaultBase, applications: List[ApplicationsModel]) -> tuple[BaseElementABC, ...]:
    argo = ArgoAdapter(argo_url=argo_base.host, token=argo_base.token)
    vault_client = VaultClient(token=vault_base.token)
    data = list()
    for app in vault_base.applications:
        data.append(tag('h3')(app))
        vault_data = vault_client.get_secret_json(app)
        logger.debug(f"[block_config_ppo] vault_data: {vault_data}")
        data.append(code(vault_client.get_secret_json(app)))

    value, column = argo.get_deployment_info(applications)
    return (
        tag('h2')('Application configuration'),
        element(pd.DataFrame(value, columns=column).to_html(index=False)),
        tag('h2')('Vault settings'),
        tuple(data),
    )


def block_result_ppo(dict_pods: Optional[dict[str, uts]]) -> tuple[BaseElementABC, ...]:
    return (
        tag('h2')('Kubernetes cluster utilization'),
        *[(tag('h3')(f'Container utilization in pod {name}'), uts_pods) for name, uts_pods in dict_pods.items()]
    )


def block_result_awr(awr: AWRReports):
    return (
        tag('h2')('AWR reports'),
        awr.to_xml()
    )
