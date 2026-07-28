from pydantic import BaseModel, Field


class PresentationPresetSummary(BaseModel):
    id: str
    name: str
    description: str | None = None
    is_default: bool = False
    is_active: bool = True
    preview: dict | None = None


class PresentationPresetDetail(PresentationPresetSummary):
    config: dict = Field(default_factory=dict)
    logo_storage_path: str | None = None
    has_logo: bool = False
    logo_url: str | None = None


class PresentationPresetCreate(BaseModel):
    id: str = Field(min_length=1, max_length=64, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=500)
    config: dict = Field(default_factory=dict)
    is_active: bool = True
    is_default: bool = False


class PresentationPresetUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    description: str | None = Field(default=None, max_length=500)
    config: dict | None = None
    is_active: bool | None = None


class PresentationDefaults(BaseModel):
    theme_id: str
    style_id: str
    template_id: str
    cover_template_id: str | None = None


class PresentationDefaultsUpdate(BaseModel):
    theme_id: str | None = None
    style_id: str | None = None
    template_id: str | None = None
    cover_template_id: str | None = None
