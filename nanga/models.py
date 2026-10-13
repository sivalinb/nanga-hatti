from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

class Contribution(BaseModel):
    model_config=ConfigDict(extra="forbid")
    memory: str = Field(min_length=10,max_length=4000)
    place_hint: str = Field(default="",max_length=120)
    theme: Literal["Water & landscape","Food & everyday life","Language & belonging","Work & making","Places & change"]="Water & landscape"
    attribution: str = Field(default="A local contributor",min_length=1,max_length=100)
    year: str = Field(default="A remembered moment",max_length=80)
    consent: bool = False
    shareable: bool = False
    ai_allowed: bool = False
    visibility: Literal["private","collection"]="private"

class Review(BaseModel):
    model_config=ConfigDict(extra="forbid")
    action: Literal["approve","reject"]
    title: str | None = Field(default=None,min_length=1,max_length=100)
    fact_ids: list[str] | None = Field(default=None,max_length=3)

class PlaceChoice(BaseModel):
    model_config=ConfigDict(extra="forbid")
    place_id: str

class Decision(BaseModel):
    model_config=ConfigDict(extra="forbid")
    action: Literal["search_sources","compose"]
    query: str = Field(default="",max_length=180)

class Composition(BaseModel):
    model_config=ConfigDict(extra="forbid")
    title: str = Field(min_length=1,max_length=100)
    reflection_prompt: str = Field(min_length=5,max_length=240)
    fact_ids: list[str] = Field(max_length=3)
