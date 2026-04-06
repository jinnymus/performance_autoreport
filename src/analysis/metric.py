from typing import Protocol, Any, Union

import numpy as np
import pandas as pd


class MetricAggregationFunction(Protocol):
    metric_name: str
    precision: int
    description: str

    def __call__(self, x: Union[pd.Series, pd.DataFrame], **kwargs) -> Any:
        ...


metric_register: list[MetricAggregationFunction] = list()


def metric(name: str, precision: int, description: str):
    def _wrapper(func: MetricAggregationFunction):
        metric_register.append(func)
        func.metric_name = name
        func.precision = precision
        func.description = description
        return func

    return _wrapper


@metric('rpm', 0, 'Requests per minute')
def rpm(x: pd.Series, **kwargs):
    print(f"[rpm] np.sum(x): {np.sum(x)} duration_time: {kwargs['duration_time']}")
    return np.sum(x) / kwargs['duration_time']


@metric('rps', 0, 'Requests per second')
def rps(x: pd.Series, **kwargs):
    return np.sum(x) / (kwargs['duration_time'] * 60)


@metric('avg', 0, 'Average response time')
def avg(x: pd.Series, **kwargs):
    return np.average(x)

@metric('pct90', 0, 'P90 response time')
def pct90(x: pd.Series, **kwargs):
    return np.percentile(x, 90)

@metric('pct95', 0, 'P95 response time')
def pct95(x: pd.Series, **kwargs):
    return np.percentile(x, 95)

@metric('resp95', 0, 'P95 response time (response)')
def resp95(x: pd.Series, **kwargs):
    return np.percentile(x, 95)

@metric('lat95', 0, 'P95 TTFB')
def lat95(x: pd.Series, **kwargs):
    return np.percentile(x, 95)

@metric('err', 0, 'Error rate')
def errorCount(x: pd.DataFrame, **kwargs):
    return np.sum(x['errorCount'])/np.sum(x['count'])*100

@metric('errors_percent', 0, 'Errors percent')
def count_error(x: pd.DataFrame, **kwargs):
    return np.sum(x['count_error'])/np.sum(x['count'])*100
