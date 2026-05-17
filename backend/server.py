"""FastAPI server exposing modular TFT odds calculations."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, model_validator

from backend.tft_odds.calculator import (
    apply_buy_policy,
    calculate_rolldown_distribution,
    calculate_shop_hit_distribution,
    calculate_slot_odds,
    chance_at_least,
    expected_value,
)
from backend.tft_odds.defaults import DEFAULT_LEVEL_ODDS, DEFAULT_POOL_SIZES_BY_TIER


Probability = Annotated[float, Field(ge=0, le=1)]
PROJECT_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIST_DIR = PROJECT_ROOT / "frontend" / "dist"
FRONTEND_ASSETS_DIR = FRONTEND_DIST_DIR / "assets"
FRONTEND_INDEX = FRONTEND_DIST_DIR / "index.html"


app = FastAPI(
    title="TFT Odds API",
    version="0.1.0",
    description=(
        "Exact slot-by-slot TFT shop odds calculator with configurable level odds, "
        "pool sizes, and rolldown economy."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if FRONTEND_ASSETS_DIR.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_ASSETS_DIR), name="assets")


@app.exception_handler(ValueError)
async def value_error_handler(_: Request, exc: ValueError) -> JSONResponse:
    """Return calculation validation errors in a consistent API shape."""

    return JSONResponse(status_code=422, content={"detail": str(exc)})


@app.get("/", include_in_schema=False)
def frontend() -> Response:
    """Serve the odds visualizer."""

    if not FRONTEND_INDEX.exists():
        return JSONResponse(
            status_code=404,
            content={
                "detail": "Frontend dev server runs separately. Start it with `npm run dev` in the frontend folder."
            },
        )
    return FileResponse(FRONTEND_INDEX)


class DefaultsResponse(BaseModel):
    level_odds: dict[int, dict[int, float]]
    pool_sizes_by_tier: dict[int, int]


class SlotOddsRequest(BaseModel):
    tier_odds: Probability = Field(
        examples=[0.24],
        description="Chance that one shop slot rolls the target unit's tier.",
    )
    target_copies_remaining: int = Field(ge=0, examples=[8])
    tier_pool_remaining: int = Field(ge=0, examples=[90])

    @model_validator(mode="after")
    def validate_pool(self) -> "SlotOddsRequest":
        if self.target_copies_remaining > self.tier_pool_remaining:
            raise ValueError("target_copies_remaining cannot exceed tier_pool_remaining")
        return self


class SlotOddsResponse(BaseModel):
    target: float
    same_tier_non_target: float
    other_tier: float


class ShopDistributionRequest(SlotOddsRequest):
    shop_slots: int = Field(default=5, ge=0, le=10)


class DistributionSummary(BaseModel):
    distribution: dict[int, float]
    expected_hits: float
    chance_at_least: dict[int, float]


class BuyPolicyRequest(BaseModel):
    shop_hits: int = Field(ge=0, examples=[2])
    copies_needed: int = Field(ge=0, examples=[3])
    gold_remaining: int = Field(ge=0, examples=[12])
    unit_cost: int = Field(gt=0, examples=[4])


class BuyPolicyResponse(BaseModel):
    copies_to_buy: int


class RolldownRequest(ShopDistributionRequest):
    copies_needed: int = Field(ge=0, examples=[3])
    gold: int = Field(ge=0, examples=[50])
    roll_cost: int = Field(default=2, gt=0)
    unit_cost: int = Field(gt=0, examples=[4])


class RolldownResponse(BaseModel):
    distribution: dict[int, float]
    expected_copies_bought: float
    chance_to_hit_goal: float
    chance_at_least: dict[int, float]


@app.get("/health", tags=["System"])
def health() -> dict[str, str]:
    """Confirm the API is running."""

    return {"status": "ok"}


@app.get("/config/defaults", response_model=DefaultsResponse, tags=["Config"])
def get_defaults() -> DefaultsResponse:
    """Return default TFT odds and pool sizes used as API examples."""

    return DefaultsResponse(
        level_odds=DEFAULT_LEVEL_ODDS,
        pool_sizes_by_tier=DEFAULT_POOL_SIZES_BY_TIER,
    )


@app.post("/odds/slot", response_model=SlotOddsResponse, tags=["Odds"])
def slot_odds(request: SlotOddsRequest) -> SlotOddsResponse:
    """Calculate one-slot odds for target, same-tier non-target, and other-tier outcomes."""

    result = calculate_slot_odds(**request.model_dump())
    return SlotOddsResponse(
        target=result.target,
        same_tier_non_target=result.same_tier_non_target,
        other_tier=result.other_tier,
    )


@app.post("/odds/shop", response_model=DistributionSummary, tags=["Odds"])
def shop_distribution(request: ShopDistributionRequest) -> DistributionSummary:
    """Calculate exact target-hit distribution for one sequentially generated shop."""

    distribution = calculate_shop_hit_distribution(**request.model_dump())
    max_hits = max(distribution.keys(), default=0)
    return DistributionSummary(
        distribution=distribution,
        expected_hits=expected_value(distribution),
        chance_at_least={
            threshold: chance_at_least(distribution, threshold)
            for threshold in range(1, max_hits + 1)
        },
    )


@app.post("/policy/buy-targets", response_model=BuyPolicyResponse, tags=["Policy"])
def buy_targets(request: BuyPolicyRequest) -> BuyPolicyResponse:
    """Calculate how many target copies are bought under the buy-every-target policy."""

    return BuyPolicyResponse(copies_to_buy=apply_buy_policy(**request.model_dump()))


@app.post("/odds/rolldown", response_model=RolldownResponse, tags=["Odds"])
def rolldown_distribution(request: RolldownRequest) -> RolldownResponse:
    """Calculate final bought-copy odds after rolling down and buying every target copy."""

    payload = request.model_dump()
    copies_needed = payload.pop("copies_needed")
    distribution = calculate_rolldown_distribution(
        copies_needed=copies_needed,
        **payload,
    )
    max_hits = max(distribution.keys(), default=0)
    return RolldownResponse(
        distribution=distribution,
        expected_copies_bought=expected_value(distribution),
        chance_to_hit_goal=chance_at_least(distribution, copies_needed),
        chance_at_least={
            threshold: chance_at_least(distribution, threshold)
            for threshold in range(1, max_hits + 1)
        },
    )
