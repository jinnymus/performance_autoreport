"""
HTTP client for optional performance-test storage APIs (e.g. POST /api/performance-tests).
"""
import logging
from datetime import datetime
from typing import Optional

import requests

logger = logging.getLogger('root')

ENV_CLINIC_REPORTS_URL = 'CLINIC_REPORTS_URL'


def send_performance_test(
    base_url: str,
    *,
    ui_version: str,
    cms_version: str,
    db_version: str,
    test_date: datetime,
    test_identifier: str,
    test_type: str,
    requests_per_second: Optional[int],
    test_description: str = '',
    test_plan: str = '',
    script_path: str = '',
    confluence_url: str = '',
    grafana_dashboard_url: str = '',
    page_response_times: Optional[list] = None,
    test_end_time: Optional[datetime] = None,
    test_passed: Optional[bool] = None,
) -> Optional[dict]:
    """
    POST aggregated performance metadata to the configured storage service.

    Returns:
        Parsed JSON response, or ``None`` on failure / skip.
    """
    if not base_url:
        logger.warning("[report_storage] CLINIC_REPORTS_URL not set, skip")
        return None

    url = base_url.rstrip('/') + '/api/performance-tests'
    payload = {
        'ui_version': ui_version,
        'cms_version': cms_version,
        'db_version': db_version or '',
        'test_date': test_date.isoformat() if hasattr(test_date, 'isoformat') else str(test_date),
        'test_identifier': test_identifier,
        'test_type': test_type,
        'requests_per_second': requests_per_second,
        'test_description': test_description,
        'test_plan': test_plan,
        'script_path': script_path,
        'confluence_url': confluence_url,
        'grafana_dashboard_url': grafana_dashboard_url,
        'page_response_times': page_response_times or [],
    }
    if test_end_time:
        payload['test_end_time'] = test_end_time.isoformat() if hasattr(test_end_time, 'isoformat') else str(test_end_time)
    if test_passed is not None:
        payload['test_passed'] = test_passed

    try:
        resp = requests.post(url, json=payload, timeout=30)
        if resp.ok:
            logger.info(f"[report_storage] Sent: {test_identifier} RPS={requests_per_second}")
            return resp.json()
        logger.warning(f"[report_storage] HTTP {resp.status_code}: {resp.text}")
        return None
    except Exception as e:
        logger.exception(f"[report_storage] Error: {e}")
        return None
