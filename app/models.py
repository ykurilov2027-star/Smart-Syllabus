from datetime import date, datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


NonEmptyText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class Deadline(ContractModel):
    title: NonEmptyText
    due_date: date | None = None
    description: str | None = None


class Topic(ContractModel):
    title: NonEmptyText
    description: str | None = None


class Score(ContractModel):
    name: NonEmptyText
    points: float = Field(ge=0, allow_inf_nan=False)
    max_points: float = Field(gt=0, allow_inf_nan=False)

    @model_validator(mode="after")
    def points_do_not_exceed_maximum(self) -> "Score":
        if self.points > self.max_points:
            raise ValueError("points cannot exceed max_points.")
        return self


class SyllabusExtraction(ContractModel):
    deadlines: list[Deadline] = Field(default_factory=list)
    topics: list[Topic] = Field(default_factory=list)
    scores: list[Score] = Field(default_factory=list)


class ParseRequest(ContractModel):
    source_text: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100000)]
    case_id: NonEmptyText | None = None


class ParseResponse(ContractModel):
    record_id: str
    result: SyllabusExtraction


class ProviderRequest(ContractModel):
    request_id: str
    source_text: str
    case_id: str | None = None
    model: str


class ProviderResponse(ContractModel):
    output_json: str
    model: str


class ApiError(ContractModel):
    kind: str
    message: str
    retryable: bool
    request_id: str


class ErrorResponse(ContractModel):
    error: ApiError


class StoredRecord(ContractModel):
    record_id: str
    result: SyllabusExtraction
    created_at: datetime


class HealthResponse(ContractModel):
    status: str
    version: str
    provider: str
    model: str
    mode: str
    storage: str
    additional_component: str
    uptime_s: float
