from datetime import datetime, timezone, timedelta
from typing import Optional, Annotated, Union

import uuid as uuid
from pydantic import Field, model_validator, field_validator, PlainSerializer
from pydantic.main import BaseModel
from pydantic_core.core_schema import ValidationInfo
from base.element import InfluxType, ServerType

DatetimeSerialization = Annotated[
    datetime, PlainSerializer(lambda x: x.strftime('%Y-%m-%d %H:%M:%S'), when_used='json')]


class PageBase(BaseModel):
    parent: Optional[int] = None
    title: Optional[str] = None
    page: Optional[str] = None

    @classmethod
    @model_validator(mode='before')
    def validate_params(cls, values):
        parent = values["parent"]
        title = values["title"]
        page = values["page"]
        if parent is None and page is None:
            raise ValueError("parent is none and page is none")
        if parent is not None and page is not None:
            raise ValueError("parent is not none and page is not none")
        if parent is not None and title is None:
            raise ValueError("title is none")
        return values


class ConfluenceBase(BaseModel):
    type: ServerType = ServerType.CONFLUENCE
    host: Optional[str] = None
    token: Optional[str] = None
    space: Optional[str] = None
    parent: Optional[str] = None
    title: Optional[str] = None
    page: Optional[str] = None
    date: Optional[str] = None

    @classmethod
    @model_validator(mode='before')
    def validate_params(cls, values):
        parent = values["parent"]
        title = values["title"]
        page = values["page"]
        if parent is None and page is None:
            raise ValueError("parent is none and page is none")
        if parent is not None and page is not None:
            raise ValueError("parent is not none and page is not none")
        if parent is not None and title is None:
            raise ValueError("title is none")
        return values


class MarkdownBase(BaseModel):
    type: ServerType = ServerType.MARKDOWN
    host: Optional[str] = None
    token: Optional[str] = None
    space: Optional[str] = None
    parent: Optional[str] = None
    title: Optional[str] = None
    page: Optional[str] = None


class InfluxBase(BaseModel):
    type: InfluxType = InfluxType.INFLUX
    url: str = "http://127.0.0.1:8086"
    host: str = "127.0.0.1"
    port: int = 8086
    db: str = "jmeter"
    user: str = "admin"
    pwd: str = "test"
    measurement: str = "jmeter"
    bucket: str = "jmeter"
    token: str = "jmeter"
    org: str = "org"


class GrafanaBase(BaseModel):
    host: str = None
    port: str = None
    snapshot_template_jmeter: str = (
        'https://grafana.example.com/d/sample-jmeter/report-jmeter-flux?'
        'timezone=browser&var-aggregation=30&var-runId={}&var-samplerType=$__all'
    )
    snapshot_template_nodejs: str = (
        'https://grafana.example.com/d/sample-pods/report-pods?'
        'var-namespace=default&var-workload={}&orgId=1'
    )
    snapshot_template_elastic: str = (
        'https://grafana.example.com/d/sample-elastic/report-request-time-analyze?orgId=1&timezone=browser'
    )
    snapshot_template_pods: str = (
        'https://grafana.example.com/d/sample-pods-metrics/report-pods-metrics?'
        'orgId=1&timezone=browser&var-namespace=default'
    )
    snapshot_template_nodes: str = (
        'https://grafana.example.com/d/sample-nodes/report-node-exporter-full?'
        'orgId=1&timezone=browser'
    )
    user: str = "admin"
    pwd: str = "admin"


class ArgoBase(BaseModel):
    host: str = "127.0.0.1"
    login: str = "test"
    password: str = "test"
    token: str = "test"


class VaultBase(BaseModel):
    token: str = "test"
    applications: list[str] = Field(default_factory=list)


class YandexBase(BaseModel):
    type: ServerType = ServerType.YANDEX
    parent: Optional[int] = None
    title: Optional[str] = None
    page: Optional[int] = None

    @classmethod
    @model_validator(mode='before')
    def validate_params(cls, values):
        parent = values["parent"]
        title = values["title"]
        page = values["page"]
        if parent is None and page is None:
            raise ValueError("parent is none and page is none")
        if parent is not None and page is not None:
            raise ValueError("parent is not none and page is not none")
        if parent is not None and title is None:
            raise ValueError("title is none")
        return values


class DashboardElement(BaseModel):
    url: str
    panels: Optional[list[int]] = Field(default_factory=list)


class LoadStepBase(BaseModel):
    name: str
    step: list = Field(default_factory=list)


class ApplicationsModel(BaseModel):
    name: Optional[str] = None
    env: Optional[str] = None
    image: Optional[str] = None
    workload: Optional[str] = None
    application: Optional[str] = None
    namespace: Optional[str] = None
    resource: Optional[str] = None
    kind: Optional[str] = None


class NodesModel(BaseModel):
    name: Optional[str] = None


class LoadBase(BaseModel):
    # uuid: uuid.UUID
    uuid: str
    start_datetime: DatetimeSerialization
    service: str
    jmx: str
    test_desc: str
    load_plan: list[list[int]]

    @field_validator('service')
    @classmethod
    def to_lower(cls, v: str, info: ValidationInfo) -> str:
        return v.lower()

    @field_validator('start_datetime')
    @classmethod
    def check_timezone(cls, v: datetime, info: ValidationInfo) -> datetime:
        moscow = timezone(timedelta(hours=3))
        if v.tzinfo and v.tzinfo.utcoffset(None) == moscow.utcoffset(None):
            return v
        return v.astimezone(tz=moscow)


class SettingsBase(BaseModel):
    ui_version: str
    cms_version: str
    db_version: str


class ExpressBase(BaseModel):
    chat_id: str
    bot_id: str
    secret_key: str
    cts_host: str


class AwrBase(BaseModel):
    host: str
    port: str
    login: str
    password: str


class OracleAwr(AwrBase):
    sid: str


class PostgresAwr(AwrBase):
    dbname: str


class RequestCreateReport(BaseModel):
    test: LoadBase = None
    settings: SettingsBase = None
    express: ExpressBase = None
    applications: list[ApplicationsModel] = Field(default_factory=list)
    # nodes: list[NodesModel] = Field(default_factory=list)
    server: Union[ConfluenceBase, YandexBase, MarkdownBase] = None
    influx: InfluxBase = None
    grafana: GrafanaBase = None
    argo: Optional[ArgoBase] = None
    vault: Optional[VaultBase] = None
    awr: Optional[Union[OracleAwr, PostgresAwr]] = None
    test_type: Optional[str] = None
    test_name: Optional[str] = None
