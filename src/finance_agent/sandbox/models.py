"""Pydantic models for sandbox CRM client profiles."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

RiskTolerance = Literal["conservative", "moderate", "growth", "aggressive"]
LifeStage = Literal["accumulation", "pre-retirement", "retirement", "legacy"]


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
