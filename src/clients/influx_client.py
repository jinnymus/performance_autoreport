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

DatetimeSerialization = Annotated[datetime, PlainSerializer(lambda x: x.strftime('%Y-%m-%d %H:%M:%S'), when_used='json')]

def export_metric_from_influx(host: str,
                              port: int,
                              db: str,
                              user: str,
                              pwd: str,
                              measurement: str,
                              start_datetime: datetime,
                              end_datetime: datetime,
                              uuid: str):
    client = DataFrameClient(host=host,
                             port=port,
                             username=user,
                             password=pwd,
                             database=db
                             )
    moscow = timezone(timedelta(hours=3))
    bind_params = {
                    'end_time': end_datetime.astimezone(tz=moscow).isoformat(timespec='seconds'),
                    'start_time': start_datetime.astimezone(tz=moscow).isoformat(timespec='seconds')
                   }
    print(f"""query: select * from {measurement}
                                        where time >= $start_time
                                        and time < $end_time""")
    # df = client.query(f"""select * from "{measurement}"
    #                                     where time >= '{start_datetime.isoformat(timespec='seconds')}'
    #                                     and time < '{end_datetime.isoformat(timespec='seconds')}'
    #                                     and "uuid" = '{uuid}'""", epoch='ns')[measurement]
    df = client.query(query=f"""select * from "script" where time >= $start_time and time < $end_time;""",
                                        epoch='ns',
                                        bind_params=bind_params).get('script')
    dfn = df[(df['transaction'] != 'internal') & (df['transaction'] != 'all') & (df['statut'] != 'all')][
        ['avg', 'count', 'pct90.0', 'pct95.0', 'statut', 'transaction']].dropna(subset=['statut']).fillna(0)
    dfn_ok = dfn[dfn['statut'] == 'ok'].set_index('transaction', append=True)
    dfn_ko = dfn[dfn['statut'] == 'ko'].set_index('transaction', append=True)
    data = dfn_ok.join(dfn_ko[['count']], rsuffix='_error').drop(['statut'], axis=1).fillna(0).reset_index().rename(columns={'index': 'time'})
    return data

