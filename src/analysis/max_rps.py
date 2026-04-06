"""
Max RPS helper for max-performance search tests.
If any response time exceeds 400 ms, that load level is considered failed.
Returns the RPS of the last step where all response times are ≤ 400 ms.
"""
import logging
from typing import Optional

import pandas as pd

logger = logging.getLogger('root')

# Response time threshold (ms); above this the step fails
RESPONSE_TIME_THRESHOLD_MS = 400

# Response-time metrics to check, in priority order
RESPONSE_TIME_METRICS = ('resp95', 'lat95', 'pct95', 'pct90', 'responseTime')


def get_max_rps_for_sla(
    data: pd.DataFrame,
    load_plan: list[list[int]],
    threshold_ms: int = RESPONSE_TIME_THRESHOLD_MS
) -> Optional[int]:
    """
    Highest RPS where all response times are ≤ threshold_ms.

    ``load_plan``: ``[[up, hold, down, load_level], ...]`` — last element per step is load (RPS).
    ``data``: DataFrame from the aggregator with MultiIndex columns ``(level_load, metric)``.

    Returns:
        RPS of the last passing step, or ``None`` if there is no data or the first step fails.
    """
    if data is None or data.empty:
        logger.warning("[max_rps] Data is empty")
        return None

    load_levels = [step[3] for step in load_plan]
    if not load_levels:
        return None

    # Pick the first available response-time metric
    rt_metric = None
    if hasattr(data.columns, 'levels'):
        for m in RESPONSE_TIME_METRICS:
            if m in data.columns.get_level_values(1):
                rt_metric = m
                break
    if rt_metric is None:
        logger.warning("[max_rps] No response time metric found in data")
        return None

    # Walk load levels in ascending order
    max_ok_rps = None
    for level in sorted(load_levels):
        col_key = (level, rt_metric)
        if col_key not in data.columns:
            continue
        col = data[col_key].dropna()
        if col.empty:
            continue
        max_val = float(col.max())
        if max_val > threshold_ms:
            logger.info(f"[max_rps] Level {level} failed: max response time {max_val}ms > {threshold_ms}ms")
            break
        max_ok_rps = level
        logger.debug(f"[max_rps] Level {level} OK: max response time {max_val}ms")

    return max_ok_rps


def extract_page_response_times(
    data: pd.DataFrame,
    load_level: Optional[int] = None
) -> list[dict]:
    """
    Build ``page_response_times`` payloads from aggregated metrics for downstream APIs.
    ``load_level``: explicit step to use; if ``None``, the last available level is used.
    """
    if data is None or data.empty:
        return []

    if not hasattr(data.columns, 'levels'):
        return []

    levels = data.columns.get_level_values(0).unique().tolist()
    level = load_level if load_level is not None and load_level in levels else (levels[-1] if levels else None)
    if level is None:
        return []

    result = []
    metric_map = {'resp95': 'pct_95', 'lat95': 'pct_95', 'pct95': 'pct_95', 'pct90': 'pct_90', 'avg': 'mean', 'rpm': None}
    for idx in data.index:
        page_name = str(idx)
        row = {'page_name': page_name, 'mean': None, 'pct_90': None, 'pct_95': None, 'pct_99': None, 'max': None, 'min': None}
        for col in data.columns:
            if col[0] != level:
                continue
            metric = col[1]
            target = metric_map.get(metric)
            if target and target in row:
                try:
                    val = data.loc[idx, col]
                    if pd.notna(val):
                        row[target] = round(float(val), 2)
                except (KeyError, TypeError):
                    pass
        if row.get('pct_95') or row.get('mean'):
            result.append(row)
    return result
