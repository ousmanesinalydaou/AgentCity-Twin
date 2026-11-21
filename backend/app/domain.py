from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

Role = Literal[
    "Super Admin", "Organization Admin", "City Operator", "Analyst", "Researcher", "Developer", "Viewer"
]
ScenarioKind = Literal[
    "Emergency",
    "Road Closure",
    "Campus Event",
    "Football Match",
    "Pollution Spike",
    "Severe Weather",
    "Transit Failure",
    "Construction",
    "Power Outage",
    "Public Gathering",
]

DIMENSIONS = (
    "traffic",
    "mobility",
    "environment",
    "safety",
    "cost",
    "complexity",
    "resilience",
    "accessibility",
    "publicImpact",
    "sustainability",
)
DEFAULT_WEIGHTS = dict(zip(DIMENSIONS, (16, 15, 10, 22, 7, 4, 8, 7, 7, 4), strict=True))
Language = Literal["en", "fr", "bm"]


class RoutingPolicy(BaseModel):
    max_cost_per_million: float | None = Field(default=None, ge=0, le=1_000_000)
    prefer_low_cost: bool = False
    require_language_match: bool = False
    prefer_advanced: bool = True


class ScenarioInput(BaseModel):
    title: str = Field(min_length=3, max_length=120)
    kind: ScenarioKind = "Emergency"
    city_id: str = Field(default="debrecen", pattern=r"^[a-z0-9-]{1,48}$")
    workspace_id: str = Field(default="city-lab", pattern=r"^[a-z0-9-]{1,48}$")
    description: str = Field(default="", max_length=2000)
    location: str = Field(default="University of Debrecen", min_length=1, max_length=120)
    coordinates: tuple[float, float] | None = None
    starts_at: datetime
    duration: int = Field(default=60, ge=15, le=720)
    severity: int = Field(default=4, ge=1, le=5)
    population: int = Field(default=1200, ge=0, le=5_000_000)
    radius: int = Field(default=850, ge=50, le=10000)
    constraints: str = Field(default="", max_length=500)
    seed: int = Field(default=42, ge=0, le=2147483647)
    provider_id: str | None = Field(default=None, max_length=48)
    compare_provider_id: str | None = Field(default=None, max_length=48)
    agent_ids: list[str] | None = Field(default=None, max_length=13)

    @field_validator("coordinates")
    @classmethod
    def bounds(cls, value):
        if value and not (-180 <= value[0] <= 180 and -85 <= value[1] <= 85):
            raise ValueError("Coordinates are outside supported map bounds.")
        return value


class Credentials(BaseModel):
    email: str = Field(min_length=3, max_length=254, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    password: str = Field(min_length=10, max_length=128)
    name: str = Field(default="", max_length=100)


class Preferences(BaseModel):
    language: Language = "en"
    theme: Literal["dark", "light", "system"] = "dark"
    notifications: bool = True


class ProviderInput(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9-]{1,48}$")
    name: str = Field(min_length=1, max_length=80)
    kind: Literal[
        "openai", "azure", "foundry", "gemini", "anthropic", "lmstudio", "ollama", "compatible", "custom"
    ]
    url: str = Field(default="", max_length=512)
    model: str = Field(min_length=1, max_length=160)
    secret: str = Field(default="", max_length=2048)
    deployment: str = Field(default="", max_length=100)
    version: str = Field(default="", max_length=40)
    organization: str = Field(default="", max_length=80)
    enabled: bool = True
    local: bool = False
    default: bool = False
    priority: int = Field(default=10, ge=0, le=1000)
    timeout: int = Field(default=15, ge=2, le=45)
    max_tokens: int = Field(default=512, ge=64, le=8192)
    context_window: int = Field(default=8192, ge=512, le=2_000_000)
    temperature: float = Field(default=0.2, ge=0, le=1)
    cost_per_million: float | None = Field(default=None, ge=0, le=1_000_000)
    languages: list[Language] = Field(default_factory=list, max_length=3)
    reasoning_tier: Literal["standard", "advanced"] = "standard"
    capabilities: list[Literal["structured", "vision", "tools", "embeddings", "streaming"]] = Field(
        default_factory=lambda: ["structured"], max_length=5
    )
