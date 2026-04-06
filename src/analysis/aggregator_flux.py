from typing import Iterable, Optional, Union

import pandas as pd
from datetime import datetime, timedelta

from analysis.metric import MetricAggregationFunction, metric_register


class AggregatorStepMetricFlux:
    def __init__(self,
                 data_source: pd.DataFrame = None,          # Raw measurements
                 operation_column: Iterable[str] = None,    # Operation name column
                 load_plan: Iterable = None,                # Load plan steps
                 start_time: datetime = None,
                 time_column: str = '_time',
                 offset: int = None,
                 offset_left: int = 0,
                 offset_right: int = 0,
                 ):
        self.data_source = data_source
        self.data_metric: dict = {}
        self.data_metric_assemble: pd.DataFrame = None
        self.operation_column = operation_column
        self.operation_name = self.data_source[self.operation_column].drop_duplicates().values
        self.load_plan = load_plan
        self.start_time = start_time
        self.end_time = self.start_time + timedelta(minutes=sum([step[0] + step[1] for step in self.load_plan])) if start_time else None
        self.time_column = time_column
        if offset:
            self.offset_left = offset
            self.offset_right = offset
        else:
            self.offset_left = offset_left
            self.offset_right = offset_right

    def shift_time_load(self):
        shift_time = 0
        for step in self.load_plan:
            up_time = step[0]
            hold_time = step[1]
            down_time = step[2]
            load_level = step[3]
            shift_time = up_time + shift_time
            duration_time = hold_time - self.offset_left - self.offset_right
            yield load_level, shift_time + self.offset_left, duration_time
            shift_time += hold_time + down_time

    def filter_operation(self, include: Optional[list[str]] = None, exclude: Optional[list[str]] = None):
        if bool(include) ^ bool(exclude):
            if include:
                pass
            if exclude:
                self.operation_name = [o for o in self.operation_name if not o in exclude]
        else:
            pass


    def metric(self, metric_group: Union[str,list[str]], func: MetricAggregationFunction, column: Optional[str] = None) -> pd.Series:
        if not func in metric_register:
            raise ValueError("Metric aggregation function is not register")
        if self.start_time is None:
            self.start_time = self.data_source[self.time_column].min() if self.start_time is None else self.start_time
            self.end_time = self.start_time + timedelta(minutes=sum([step[0] + step[1] for step in self.load_plan]))
        self.data_metric[func.metric_name] = pd.DataFrame()
        for load_level, shift_time, duration_time in self.shift_time_load():
            #print(f"[metric] self.start_time: {self.start_time} load_level: {load_level} shift_time: {shift_time} duration_time: {duration_time}")
            #print(f"[metric] self.data_source: {self.data_source}")
            #print(f"[metric] self.operation_name: {self.operation_name}")
            #print(f"[metric] self.operation_column: {self.operation_column}")
            #print(f"[metric] start_time: {self.start_time} + timedelta: {self.start_time + timedelta(minutes=shift_time)}")
            # Debug variants (fixed window) kept for reference:
            # mask_time_start = self.data_source[self.time_column] >= self.start_time
            # mask_time_end = self.data_source[self.time_column] < self.start_time + timedelta(minutes=shift_time + duration_time)
            # Active window: shifted by step start
            mask_time_start = self.data_source[self.time_column] >= self.start_time + timedelta(minutes=shift_time)
            mask_time_end = self.data_source[self.time_column] < self.start_time + timedelta(minutes=shift_time + duration_time)

            # Per-operation slice for this window
            temp = self.data_source.loc[self.data_source[self.operation_column].isin(self.operation_name)].loc[mask_time_start & mask_time_end,]
            #print(f"[metric] temp: {temp}")
            temp = temp.groupby([self.operation_column], dropna=False)[metric_group].agg(func, load_level=load_level, duration_time=duration_time)
            #print(f"[metric] temp: {temp}")
            if column:
                temp = temp[column]
            temp = temp.rename(func.metric_name).round(func.precision)
            temp.index = pd.MultiIndex.from_arrays([temp.index, [load_level] * temp.index.size], names=('operation', 'level_load'))
            if self.data_metric[func.metric_name].empty:
                self.data_metric[func.metric_name] = temp
            else:
                self.data_metric[func.metric_name] = pd.concat([self.data_metric[func.metric_name], temp])
        #print(f"[metric] data_metric: {self.data_metric}")
        #print(f"[metric] data_metric: {self.data_metric[func.metric_name]}")
        return self.data_metric[func.metric_name]


    def assemble_data_metric(self) -> pd.DataFrame:
        def convert_data_for_assemble(data: pd.DataFrame) -> pd.DataFrame:
            metric = data.name
            data = pd.pivot(data.to_frame().reset_index(), values=metric, index=['operation'], columns=['level_load'])
            data.columns = pd.MultiIndex.from_arrays([data.columns.values, [metric] * data.columns.size], names=('level_load', 'metric'))
            return data

        if self.data_metric:
            self.data_metric_assemble = pd.concat([convert_data_for_assemble(data) for data in self.data_metric.values()], axis=1)
            self.data_metric_assemble = self.data_metric_assemble.reindex(sorted(self.data_metric_assemble.columns), axis=1)
            return self.data_metric_assemble
        else:
            raise ValueError('Data metric is empty')

    @classmethod
    def build_load_metric(cls, df: pd.DataFrame):
        lsm = cls()
        lsm.operation_name = list(df.index.values)
        for label, content in df.items():
            metric = label[1]
            alias = label[0]
            if metric not in lsm.data_metric:
                lsm.data_metric[metric] = {}
            lsm.data_metric[metric][alias] = content
        return lsm
