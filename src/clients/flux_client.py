from datetime import datetime, timezone, timedelta
from influxdb import DataFrameClient
from influxdb_client import InfluxDBClient, Point, Dialect
import pytz
import time
from typing import Optional, Annotated, Union
from pydantic import Field, model_validator, field_validator, PlainSerializer
from pydantic.main import BaseModel
from pydantic_core.core_schema import ValidationInfo
# from analysis.metric import *
# from analysis.metric import count_error, pct90, rpm
from analysis.metric import MetricAggregationFunction, metric_register
from analysis.aggregator_influx import AggregatorStepMetric
import pandas as pd
DatetimeSerialization = Annotated[datetime, PlainSerializer(lambda x: x.strftime('%Y-%m-%d %H:%M:%S'), when_used='json')]


def export_metric_from_flux_v2(url: str,
                              org: str,
                              bucket: str,
                              token: str,
                              start_datetime: datetime,
                              end_datetime: datetime,
                              uuid: str):
    print(f"[export_metric_from_influx2] url: {url}")
    client = InfluxDBClient(url=url, token=token, org=org, timeout=30000)
    query_api = client.query_api()
    """
    Query: using Pandas DataFrame
    """
    p = { "_start" : start_datetime,
          "_end": end_datetime,
        }
    print(f"[export_metric_from_influx2] time: {p}")
    _aggregation = "5"
    if uuid == "":
        query_all = f"""
                    from(bucket: "{bucket}")
                    |> range(start: _start, stop: _end)
                    |> filter(fn: (r) => r["_measurement"] == "requestsRaw")
                    |> keep(columns: ["_time","_field","_value","requestName"])
                    |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")"""
    else:
        query_all = f"""
                    from(bucket: "{bucket}")
                    |> range(start: _start, stop: _end)
                    |> filter(fn: (r) => r["_measurement"] == "requestsRaw")
                    |> filter(fn: (r) => r["runId"] =~ /{uuid}/)
                    |> keep(columns: ["_time","_field","_value","requestName"])
                    |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")"""
    print(f"[export_metric_from_flux_v2] query_all: {query_all}")
    data_frame = query_api.query_data_frame(query_all,params=p,data_frame_index=['_time'])
    if isinstance(data_frame, list):
        if len(data_frame) > 1:
            print(f"[export_metric_from_influx2] len > 1")
            data_frame_final = pd.concat(data_frame)
        elif len(data_frame) == 1:
            print(f"[export_metric_from_influx2] len == 1")
            data_frame_final = data_frame[0]
        else:
            print(f"[export_metric_from_influx2] else")
            data_frame_final = pd.DataFrame()  # Empty DataFrame if no data
    else:
        print(f"[export_metric_from_influx2] not list")
        # If the query only returns a single table, it might directly return a DataFrame
        data_frame_final = data_frame
    if len(data_frame_final) == 0:
        print(f"[export_metric_from_influx2] data_frame: {data_frame_final}")
        print('[export_metric_from_influx2] DataFrame is empty!')
        client.close()
        return None
    else:
        print(f"[export_metric_from_influx2] data_frame: {data_frame_final}")
    #print(f"[export_metric_from_influx2] data_frame: {data_frame}")
    data_frame_final = data_frame_final.reset_index().rename(columns={'index': 'time'})
    if data_frame_final.empty:
        print('[export_metric_from_influx2] DataFrame is empty!')
        client.close()
        return None
    else:
        return data_frame_final


def export_metric_from_flux(url: str,
                            org: str,
                            bucket: str,
                            token: str,
                            start_datetime: datetime,
                            end_datetime: datetime,
                            uuid: str,
                            aggregation: str = "1"):
    client = InfluxDBClient(url=url, token=token, org=org)
    query_api = client.query_api()
    """
    Query: using Pandas DataFrame
    """
    p = { "_start" : start_datetime,
          "_end": end_datetime
        }

    query_all = f"""query_reponse_time_95pct = from(bucket: "{bucket}")
                |> range(start: _start, stop: _end)
                |> filter(fn: (r) => r["_measurement"] == "requestsRaw")
                |> filter(fn: (r) => r["_field"] == "responseTime")
                |> filter(fn: (r) => r["runId"] =~ /{uuid}/)
                |> filter(fn: (r) => r["result"] == "pass")
                |> filter(fn: (r) => r["samplerType"] =~ /(transaction)/)
                |> group (columns: ["requestName"])""" \
                '|> toFloat()' \
                f'|> aggregateWindow( column: "_value",every: {aggregation}s, fn: (t=<-, column) => t |> quantile(q: 0.95), createEmpty: false)' \
                '|> group (columns: ["requestName"])' \
                '|> quantile(q: 0.95)' \
                '|> group(columns: ["requestName"])' \
                '|> rename(columns: {"_value": "ResponseTime 95pct"})' \
                '|> map(fn: (r) => ({ r with _value: float(v: r._value /float' \
                f'(v: {aggregation})' \
                ') }))' \
                '|> keep(columns: ["ResponseTime 95pct", "requestName"]) ' \
                '' \
                '' \
                f""" query_latency_95pct = from(bucket: "{bucket}")
                |> range(start: _start, stop: _end)
                |> filter(fn: (r) => r["_measurement"] == "requestsRaw")
                |> filter(fn: (r) => r["_field"] == "latency")
                |> filter(fn: (r) => r["runId"] =~ /{uuid}/)
                |> filter(fn: (r) => r["result"] == "pass")
                |> filter(fn: (r) => r["samplerType"] =~ /(transaction)/)
                |> group (columns: ["requestName"])""" \
                '|> toFloat()' \
                f'|> aggregateWindow( column: "_value",every: {aggregation}s, fn: (t=<-, column) => t |> quantile(q: 0.95), createEmpty: false)' \
                '|> group(columns: ["requestName"])' \
                '|> quantile(q: 0.95)' \
                '|> group(columns: ["requestName"])' \
                '|> rename(columns: {"_value": "Latency 95pct"})' \
                '|> map(fn: (r) => ({ r with _value: float(v: r._value /float' \
                f'(v: {aggregation})' \
                ') }))' \
                '|> keep(columns: ["Latency 95pct", "requestName"]) ' \
                '' \
                '' \
                f' query_rps = from(bucket: "{bucket}")' \
                '|> range(start: _start, stop: _end)' \
                '|> filter(fn: (r) => r["_measurement"] == "requestsRaw")' \
                '|> filter(fn: (r) => r["_field"] == "responseTime")' \
                '|> filter(fn: (r) => r["result"] == "pass")' \
                f'|> filter(fn: (r) => r["runId"] =~ /{uuid}/)' \
                '|> filter(fn: (r) => r["samplerType"] =~ /(transaction)/)' \
                '|> group(columns: ["requestName"])' \
                f'|> aggregateWindow(every: {aggregation}s, fn: count, createEmpty: false)' \
                '|> toFloat()' \
                '|> group(columns: ["requestName"])' \
                '|> quantile(q: 0.95)' \
                '|> group(columns: ["requestName"])' \
                '|> map(fn: (r) => ({ r with _value: ' \
                f'float(v: r._value /float(v: {aggregation}))' \
                '}))' \
                '|> rename(columns: {"_value": "RPS"})' \
                '|> keep(columns: ["RPS", "requestName"]) ' \
                '' \
                '' \
                ' failuresPercentages = () => {' \
                f'countResponseTime=from(bucket: "{bucket}")' \
                '|> range(start: _start, stop: _end)' \
                '|> filter(fn: (r) => r["_measurement"] == "requestsRaw")' \
                '|> filter(fn: (r) => r["_field"] == "responseTime")' \
                f'|> filter(fn: (r) => r["runId"] =~ /{uuid}/)' \
                '|> filter(fn: (r) => r["samplerType"] =~ /(transaction)/)' \
                '|> group(columns: ["requestName"] )' \
                '|> count()' \
                '|> group()' \
                '|> toFloat()' \
                '|> keep(columns: ["_value", "requestName"])' \
                f' sumerrorCount=from(bucket: "{bucket}")' \
                '|> range(start: _start, stop: _end)' \
                '|> filter(fn: (r) => r["_measurement"] == "requestsRaw")' \
                '|> filter(fn: (r) => r["_field"] == "errorCount")' \
                f'|> filter(fn: (r) => r["runId"] =~ /{uuid}/)' \
                '|> filter(fn: (r) => r["samplerType"] =~ /(transaction)/)' \
                '|> group(columns: ["requestName"] )' \
                '|> sum()' \
                '|> group()' \
                '|> toFloat()' \
                '|> keep(columns: ["_value", "requestName"])' \
                'return join(' \
                '    tables:{countResponseTime:countResponseTime, sumerrorCount:sumerrorCount},' \
                '    on:["requestName"]' \
                '    )' \
                '    |> map(fn:(r) => ({' \
                '            requestName: r.requestName,' \
                '            Errors: (r._value_sumerrorCount / r._value_countResponseTime) * 100.0' \
                '    }))' \
                '}' \
                'ResultTable1 = join(tables: {tTmp1: query_rps, tTmp2: failuresPercentages()}, on: ["requestName"], method: "inner")' \
                'ResultTable2 = join(tables: {tTmp3: query_reponse_time_95pct, tTmp4: query_latency_95pct}, on: ["requestName"], method: "inner")' \
                'ResultTable = join(tables: {tTmp5: ResultTable1, tTmp6: ResultTable2}, on: ["requestName"], method: "inner")' \
                'ResultTable ' \
                '|> rename(columns: {"requestName": "RequestName"})' \
                '|> rename(columns: {"Errors": "Errors Pct"})' \
                '|> keep(columns: ["RequestName","ResponseTime 95pct","Latency 95pct","RPS","Errors Pct"])' \
                '|> yield()'

    data_frame = query_api.query_data_frame(query_all, params=p)

    """
    Close client
    """
    client.close()
    data_frame = data_frame[["RequestName","RPS","Latency 95pct","ResponseTime 95pct","Errors Pct"]]
    return data_frame
