import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.estimates.form_fields import validate_template_fields
from app.form_templates.categories import (
    DEFAULT_NATURE_OF_WORK_CATEGORY,
    DEFAULT_TEMPLATE_LANGUAGE,
    validate_nature_of_work_category,
    validate_template_language,
)


class LocalizedText(BaseModel):
    en: str = ""
    ja: str = ""


class SelectOptionSchema(BaseModel):
    value: str
    label: LocalizedText


class FormFieldSchema(BaseModel):
    key: str
    type: str
    required: bool = True
    sort_order: int = 0
    label: LocalizedText
    description: LocalizedText = Field(default_factory=LocalizedText)
    placeholder: LocalizedText = Field(default_factory=LocalizedText)
    options: list[SelectOptionSchema] = Field(default_factory=list)


class FormTemplateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    fields: list[dict[str, Any]]
    nature_of_work_category: str
    language: str
    is_default: bool
    created_at: datetime
    updated_at: datetime


class FormTemplateSummary(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    nature_of_work_category: str
    language: str
    is_default: bool
    field_count: int


class FormTemplateOption(BaseModel):
    id: uuid.UUID
    name: str
    nature_of_work_category: str
    language: str
    is_default: bool


class FormTemplateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=500)
    fields: list[dict[str, Any]]
    nature_of_work_category: str = DEFAULT_NATURE_OF_WORK_CATEGORY
    language: str = DEFAULT_TEMPLATE_LANGUAGE
    is_default: bool = False

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("Name is required")
        return trimmed

    @field_validator("nature_of_work_category")
    @classmethod
    def validate_category(cls, value: str) -> str:
        return validate_nature_of_work_category(value)

    @field_validator("language")
    @classmethod
    def validate_language(cls, value: str) -> str:
        return validate_template_language(value)

    @field_validator("fields")
    @classmethod
    def validate_fields(cls, value: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return validate_template_fields(value)


class FormTemplateUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=500)
    fields: list[dict[str, Any]] | None = None
    nature_of_work_category: str | None = None
    language: str | None = None
    is_default: bool | None = None

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("Name is required")
        return trimmed

    @field_validator("nature_of_work_category")
    @classmethod
    def validate_category(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return validate_nature_of_work_category(value)

    @field_validator("language")
    @classmethod
    def validate_language(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return validate_template_language(value)

    @field_validator("fields")
    @classmethod
    def validate_fields(
        cls,
        value: list[dict[str, Any]] | None,
    ) -> list[dict[str, Any]] | None:
        if value is None:
            return None
        return validate_template_fields(value)
