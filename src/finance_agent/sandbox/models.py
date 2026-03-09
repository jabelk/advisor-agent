"""Pydantic models for sandbox CRM client profiles."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

RiskTolerance = Literal["conservative", "moderate", "growth", "aggressive"]
LifeStage = Literal["accumulation", "pre-retirement", "retirement", "legacy"]


VALID_RISK_TOLERANCES = {"conservative", "moderate", "growth", "aggressive"}
VALID_LIFE_STAGES = {"accumulation", "pre-retirement", "retirement", "legacy"}


class CompoundFilter(BaseModel):
    """Multi-dimensional client query filter used across all list-builder stories."""

    min_age: int | None = None
    max_age: int | None = None
    min_value: float | None = None
    max_value: float | None = None
    risk_tolerances: list[str] | None = None
    life_stages: list[str] | None = None
    not_contacted_days: int | None = None
    contacted_after: str | None = None
    contacted_before: str | None = None
    search: str | None = None
    sort_by: Literal["account_value", "age", "last_name", "last_interaction_date"] = "account_value"
    sort_dir: Literal["asc", "desc"] = "desc"
    limit: int = Field(default=50, gt=0)

    @model_validator(mode="after")
    def _validate_ranges(self) -> CompoundFilter:
        if self.min_age is not None and self.min_age < 0:
            raise ValueError("min_age must be >= 0")
        if self.max_age is not None and self.max_age < 0:
            raise ValueError("max_age must be >= 0")
        if self.min_age is not None and self.max_age is not None and self.min_age > self.max_age:
            raise ValueError("min_age must be <= max_age")
        if self.min_value is not None and self.min_value < 0:
            raise ValueError("min_value must be >= 0")
        if self.max_value is not None and self.max_value < 0:
            raise ValueError("max_value must be >= 0")
        if (
            self.min_value is not None
            and self.max_value is not None
            and self.min_value > self.max_value
        ):
            raise ValueError("min_value must be <= max_value")
        if self.not_contacted_days is not None and self.not_contacted_days <= 0:
            raise ValueError("not_contacted_days must be > 0")
        if self.contacted_after is not None and self.contacted_before is not None:
            if self.contacted_after > self.contacted_before:
                raise ValueError("contacted_after must be <= contacted_before")
        if self.not_contacted_days is not None and (
            self.contacted_after is not None or self.contacted_before is not None
        ):
            raise ValueError(
                "not_contacted_days is mutually exclusive with contacted_after/contacted_before"
            )
        if self.risk_tolerances:
            for v in self.risk_tolerances:
                if v not in VALID_RISK_TOLERANCES:
                    raise ValueError(f"Invalid risk tolerance: {v}")
        if self.life_stages:
            for v in self.life_stages:
                if v not in VALID_LIFE_STAGES:
                    raise ValueError(f"Invalid life stage: {v}")
        return self

    def describe(self) -> str:
        """Return a human-readable summary of active filters."""
        parts: list[str] = []
        if self.min_age is not None and self.max_age is not None:
            parts.append(f"age {self.min_age}–{self.max_age}")
        elif self.min_age is not None:
            parts.append(f"age >= {self.min_age}")
        elif self.max_age is not None:
            parts.append(f"age <= {self.max_age}")
        if self.min_value is not None and self.max_value is not None:
            parts.append(f"value ${self.min_value:,.0f}–${self.max_value:,.0f}")
        elif self.min_value is not None:
            parts.append(f"value >= ${self.min_value:,.0f}")
        elif self.max_value is not None:
            parts.append(f"value <= ${self.max_value:,.0f}")
        if self.risk_tolerances:
            parts.append(f"risk: {', '.join(self.risk_tolerances)}")
        if self.life_stages:
            parts.append(f"stage: {', '.join(self.life_stages)}")
        if self.not_contacted_days is not None:
            parts.append(f"not contacted in {self.not_contacted_days} days")
        if self.contacted_after and self.contacted_before:
            parts.append(f"contacted {self.contacted_after} to {self.contacted_before}")
        elif self.contacted_after:
            parts.append(f"contacted after {self.contacted_after}")
        elif self.contacted_before:
            parts.append(f"contacted before {self.contacted_before}")
        if self.search:
            parts.append(f'search: "{self.search}"')
        parts.append(f"sorted by {self.sort_by} ({self.sort_dir})")
        if self.limit != 50:
            parts.append(f"limit {self.limit}")
        return " | ".join(parts) if parts else "no filters"


class SavedList(BaseModel):
    """A named, persisted filter definition for reusable client lists."""

    name: str
    description: str = ""
    filters: CompoundFilter
    created_at: str  # ISO 8601
    last_run_at: str | None = None


class QueryInterpretation(BaseModel):
    """Result of translating a natural language query into a CompoundFilter."""

    original_query: str
    filters: CompoundFilter
    filter_mapping: dict[str, str]
    unrecognized: list[str] = []
    confidence: Literal["high", "medium", "low"]


ActivityType = Literal["call", "meeting", "email", "other"]
TaskPriority = Literal["High", "Normal", "Low"]

VALID_ACTIVITY_TYPES = {"call", "meeting", "email", "other"}

ADVISOR_AGENT_TAG = "[advisor-agent]"


class TaskCreate(BaseModel):
    """Input validation for creating a follow-up task."""

    subject: str = Field(min_length=1, max_length=255)
    due_date: str | None = None  # YYYY-MM-DD; defaults to today + 7 days
    priority: TaskPriority = "Normal"


class TaskSummary(BaseModel):
    """Summary counts for the task dashboard."""

    total_open: int = 0
    overdue: int = 0
    due_today: int = 0
    due_this_week: int = 0


class ClientCreate(BaseModel):
    """Input validation for creating or editing a client."""

    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    age: int = Field(ge=18, le=100)
    occupation: str = Field(min_length=1, max_length=200)
    email: str = Field(min_length=1)
    phone: str = Field(min_length=1)
    account_value: float = Field(ge=0)
    risk_tolerance: RiskTolerance
    life_stage: LifeStage
    investment_goals: str | None = None
    household_members: str | None = None
    notes: str | None = None


class ClientSummary(BaseModel):
    """Summary view for client lists."""

    id: int
    first_name: str
    last_name: str
    account_value: float
    risk_tolerance: RiskTolerance
    life_stage: LifeStage
    last_interaction_date: str | None = None


class InteractionRecord(BaseModel):
    """A single client interaction."""

    id: int
    interaction_date: str
    interaction_type: str
    summary: str
    created_at: str


class ClientProfile(BaseModel):
    """Full client profile with interaction history."""

    id: int
    first_name: str
    last_name: str
    age: int
    occupation: str
    email: str
    phone: str
    account_value: float
    risk_tolerance: RiskTolerance
    life_stage: LifeStage
    investment_goals: str | None = None
    household_members: str | None = None
    notes: str | None = None
    created_at: str
    updated_at: str
    interactions: list[InteractionRecord] = []
