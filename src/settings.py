from typing import Type, Any

from pydantic.fields import FieldInfo
from pydantic_settings import (
    BaseSettings,
    EnvSettingsSource,
    PydanticBaseSettingsSource, SettingsConfigDict, DotEnvSettingsSource,
)


class SettingSource(EnvSettingsSource):
    def prepare_field_value(
            self, field_name: str, field: FieldInfo, value: Any, value_is_complex: bool
    ) -> Any:
        if field_name == 'operation_filter' and value:
            return [str(x).strip().lower() for x in value.split(',')]
        return super().prepare_field_value(field_name, field, value, value_is_complex)


class DotSettingSource(DotEnvSettingsSource):
    def prepare_field_value(
            self, field_name: str, field: FieldInfo, value: Any, value_is_complex: bool
    ) -> Any:
        if field_name == 'operation_filter' and value:
            return [str(x).strip().lower() for x in value.split(',')]
        return super().prepare_field_value(field_name, field, value, value_is_complex)


class Settings(BaseSettings):
    confluence_host: str = "http://localhost:8090"
    confluence_space: str = "DOCS"
    confluence_login: str = "admin"
    confluence_password: str = "changeme"

    yandex_host: str = "https://wiki.yandex.ru"
    yandex_login: str = ""
    yandex_password: str = ""

    grafana_snapshot_host: str = "127.0.0.1"
    grafana_snapshot_port: int = 3000
    grafana_snapshot_uuid: str = "dashboard-uid"
    grafana_snapshot_template_jmeter: str = (
        "https://grafana.example.com/d/sample/report-jmeter-flux?"
        "timezone=browser&var-aggregation=30&var-runId={}&var-samplerType=$__all"
    )
    grafana_snapshot_template_jmeter_add: str = "?timezone=browser&var-aggregation=30&var-runId={}&var-samplerType=$__all"
    grafana_login: str = "admin"
    grafana_password: str = "changeme"

    argo_host: str = "argocd.example.com"
    argo_login: str = ""
    argo_password: str = ""

    influx_host: str = "127.0.0.1"
    influx_port: int = 8086
    influx_db: str = "jmeter"
    influx_user: str = ""
    influx_pwd: str = ""
    influx_measurement: str = "jmeter"

    operation_filter: list[str] = ["test"]

    @classmethod
    def settings_customise_sources(
            cls,
            settings_cls: Type[BaseSettings],
            init_settings: PydanticBaseSettingsSource,
            env_settings: PydanticBaseSettingsSource,
            dotenv_settings: PydanticBaseSettingsSource,
            file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return init_settings, SettingSource(settings_cls), DotSettingSource(settings_cls), file_secret_settings


settings = Settings()
