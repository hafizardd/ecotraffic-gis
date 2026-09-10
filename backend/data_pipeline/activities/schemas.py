from __future__ import annotations

from datetime import date, datetime, time
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .constants import EXTRACTION_VERSION, PROMPT_VERSION, SOURCE_TYPE


PassengerLevel = Literal["very_low", "low", "moderate", "high", "very_high", "unknown"]
AccessLevel = Literal["good", "moderate", "poor", "unknown"]
ConditionLevel = Literal["excellent", "good", "moderate", "poor", "very_poor", "unknown"]
IssueCategory = Literal[
    "cleanliness", "maintenance", "accessibility", "pedestrian", "lighting",
    "signage", "facility", "safety", "parking", "traffic", "environment",
]
IssueSeverity = Literal["low", "moderate", "high", "unknown"]
PlaceCategory = Literal[
    "school", "university", "hospital", "market", "park", "tourism",
    "government", "commercial", "residential", "religious",
    "transportation", "office", "hotel", "restaurant",
]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class UsageInfo(StrictModel):
    passenger_count: int | None = Field(default=None, ge=0)
    passenger_level: PassengerLevel = "unknown"
    boarding_activity: bool | None = None
    bus_present: bool | None = None
    traffic_activity: PassengerLevel = "unknown"


class FacilitiesInfo(StrictModel):
    has_seating: bool | None = None
    seating_capacity: int | None = Field(default=None, ge=0)
    has_roof: bool | None = None
    has_shelter: bool | None = None
    has_route_information: bool | None = None
    has_signage: bool | None = None
    has_staff: bool | None = None
    has_lighting: bool | None = None
    has_fan: bool | None = None
    has_water_facility: bool | None = None
    has_bicycle_parking: bool | None = None
    has_motorcycle_parking: bool | None = None
    has_wifi: bool | None = None
    has_ticket_counter: bool | None = None
    has_zebra_crossing: bool | None = None
    has_trash_bin: bool | None = None


class AccessibilityInfo(StrictModel):
    wheelchair_access: bool | None = None
    ramp_available: bool | None = None
    pedestrian_access: AccessLevel = "unknown"
    sidewalk_condition: AccessLevel = "unknown"
    stairs_access: bool | None = None
    accessibility_issues: list[str] = Field(default_factory=list)


class ConditionInfo(StrictModel):
    cleanliness: ConditionLevel = "unknown"
    maintenance: ConditionLevel = "unknown"
    structural_condition: ConditionLevel = "unknown"
    lighting_condition: ConditionLevel = "unknown"
    signage_condition: ConditionLevel = "unknown"
    vandalism: bool | None = None


class EnvironmentInfo(StrictModel):
    nearby_places: list[str] = Field(default_factory=list)
    nearby_place_categories: list[PlaceCategory] = Field(default_factory=list)
    activity_context: list[str] = Field(default_factory=list)
    landmark_categories: list[PlaceCategory] = Field(default_factory=list)

    @field_validator("nearby_places", "nearby_place_categories", "activity_context", "landmark_categories")
    @classmethod
    def deduplicate_lists(cls, value: list[str]) -> list[str]:
        return list(dict.fromkeys(item.strip() for item in value if item and item.strip()))


class Issue(StrictModel):
    category: IssueCategory
    issue: str = Field(min_length=1)
    severity: IssueSeverity = "unknown"
    evidence: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)


class SemanticExtraction(StrictModel):
    usage: UsageInfo = Field(default_factory=UsageInfo)
    facilities: FacilitiesInfo = Field(default_factory=FacilitiesInfo)
    accessibility: AccessibilityInfo = Field(default_factory=AccessibilityInfo)
    condition: ConditionInfo = Field(default_factory=ConditionInfo)
    environment: EnvironmentInfo = Field(default_factory=EnvironmentInfo)
    issues: list[Issue] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    recommendation_tags: list[str] = Field(default_factory=list)
    evidence: dict[str, str] = Field(default_factory=dict)
    confidence: dict[str, float] = Field(default_factory=dict)

    @field_validator("strengths", "weaknesses", "recommendation_tags")
    @classmethod
    def clean_lists(cls, value: list[str]) -> list[str]:
        return list(dict.fromkeys(item.strip() for item in value if item and item.strip()))

    @field_validator("confidence")
    @classmethod
    def validate_confidences(cls, value: dict[str, float]) -> dict[str, float]:
        invalid = [key for key, score in value.items() if not 0.0 <= score <= 1.0]
        if invalid:
            raise ValueError(f"confidence outside 0..1 for: {', '.join(invalid)}")
        return value


class ProvenanceInfo(StrictModel):
    source_file: str
    source_row: int = Field(ge=2)
    processed_at: datetime
    extraction_provider: Literal["openrouter"]
    extraction_model: str
    extraction_version: str = EXTRACTION_VERSION
    prompt_version: str = PROMPT_VERSION
    request_id: str | None = None
    extraction_status: Literal["llm_validated", "cache_hit", "deterministic_only"]


class SurveyKnowledgeRecord(StrictModel):
    knowledge_id: str
    source_type: Literal["survey_activity"] = SOURCE_TYPE
    source_activity_id: str
    observation_id: str

    stop_id: str | None = None
    stop_name: str | None = None
    stop_name_raw: str | None = None
    stop_name_normalized: str | None = None
    entity_resolution_confidence: float = Field(ge=0.0, le=1.0)
    entity_resolution_status: str

    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    coordinates_valid: bool

    created_at_utc: datetime | None = None
    created_at_local: datetime | None = None
    observed_date: date | None = None
    observed_time: time | None = None
    observed_at: datetime | None = None
    observed_time_source: str | None = None
    observed_time_confidence: float = Field(ge=0.0, le=1.0)
    day_of_week: str | None = None
    time_period: str | None = None

    usage: UsageInfo
    facilities: FacilitiesInfo
    accessibility: AccessibilityInfo
    condition: ConditionInfo
    environment: EnvironmentInfo
    issues: list[Issue]
    strengths: list[str]
    weaknesses: list[str]
    recommendation_tags: list[str]
    evidence: dict[str, str]
    confidence: dict[str, float]

    title_raw: str
    title_normalized: str
    description_raw: str
    description_normalized: str

    image_urls: list[str]
    video_urls: list[str]
    image_count: int = Field(ge=0)
    video_count: int = Field(ge=0)
    media_valid: bool

    duplicate_group_id: str | None = None
    duplicate_status: str
    social_metadata: dict[str, Any] = Field(default_factory=dict)
    provenance: ProvenanceInfo

    @model_validator(mode="after")
    def validate_coordinate_pair(self) -> "SurveyKnowledgeRecord":
        if self.coordinates_valid != (self.latitude is not None and self.longitude is not None):
            raise ValueError("coordinates_valid must match the presence of a valid coordinate pair")
        if self.observed_at is not None and not self.observed_time_source:
            raise ValueError("observed_at requires observed_time_source")
        return self


class RagDocument(StrictModel):
    document_id: str
    knowledge_id: str
    text: str
    metadata: dict[str, object]


class RagChunk(StrictModel):
    chunk_id: str
    knowledge_id: str
    chunk_type: Literal[
        "overview", "usage", "facilities", "accessibility", "condition",
        "environment", "issues", "recommendation_evidence",
    ]
    text: str
    metadata: dict[str, object]
