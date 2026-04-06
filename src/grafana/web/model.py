from typing import Optional

from pydantic import BaseModel, Field
from pydantic.v1 import root_validator


class DashboardElement(BaseModel):
    title: Optional[str] = Field(default=None)
    id: Optional[int] = Field(default=None)
    type: Optional[str] = Field(default=None)


class DashboardElementResponse(DashboardElement):
    url: Optional[str] = Field(default=None)


class Dashboard(BaseModel):
    url_dashboard: str = Field(alias='url')
    element_dashboard: Optional[list[int]] = Field(alias='panels', default_factory=list)

    class Config:
        json_schema_extra = {
            "example": {
                "url": "",
                "panels": []
            }
        }