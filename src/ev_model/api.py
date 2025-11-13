"""FastAPI router exposing EV financial modelling endpoints."""

from __future__ import annotations

from typing import Any, Dict, Optional

try:  # pragma: no cover - exercised conditionally when fastapi is available
    from fastapi import APIRouter, Body, HTTPException
    from pydantic import BaseModel, Field, validator
except ModuleNotFoundError:  # pragma: no cover - FastAPI not installed in minimal environments
    APIRouter = None  # type: ignore
    Body = None  # type: ignore
    HTTPException = None  # type: ignore
    BaseModel = object  # type: ignore
    Field = lambda *args, **kwargs: None  # type: ignore

    def validator(*_args, **_kwargs):  # type: ignore
        def _decorator(func):
            return func

        return _decorator
else:

    class VehicleSpecsModel(BaseModel):
        name: str = Field(..., description="Vehicle name")
        purchase_price: float = Field(..., ge=0)
        battery_capacity_kwh: float = Field(..., ge=0)
        epa_range_miles: float = Field(..., ge=0)
        efficiency_kwh_per_mile: float = Field(..., gt=0)
        warranty_years: int = Field(..., ge=0)
        warranty_miles: float = Field(..., ge=0)
        battery_replacement_cost: float = Field(..., ge=0)
        annual_registration_fee: float = Field(..., ge=0)
        annual_insurance_cost: float = Field(..., ge=0)
        maintenance_cost_per_mile: float = Field(..., ge=0)

    class FinancingModel(BaseModel):
        loan_amount: float = Field(..., ge=0)
        down_payment: float = Field(..., ge=0)
        loan_term_years: int = Field(..., ge=0)
        annual_interest_rate: float = Field(..., ge=0)

    class EnergyModel(BaseModel):
        electricity_rate_per_kwh: float = Field(..., ge=0)
        home_charging_efficiency: float = Field(..., gt=0, le=1)
        dc_fast_charging_efficiency: float = Field(..., gt=0, le=1)
        annual_miles_driven: float = Field(..., ge=0)
        percent_home_charged: float = Field(..., ge=0, le=1)
        percent_dc_charged: float = Field(..., ge=0, le=1)
        percent_level2_charged: float = Field(..., ge=0, le=1)

        @validator(
            "percent_home_charged",
            "percent_dc_charged",
            "percent_level2_charged",
        )
        def _validate_mix(cls, _value: float, values: Dict[str, Any]) -> float:
            mix = sum(
                values.get(field, 0.0)
                for field in (
                    "percent_home_charged",
                    "percent_dc_charged",
                    "percent_level2_charged",
                )
            )
            if abs(mix - 1.0) > 1e-4:
                raise ValueError("Charging mix must sum to 1.0")
            return _value

    class IncentivesModel(BaseModel):
        federal_tax_credit: float = Field(0, ge=0)
        state_tax_credit: float = Field(0, ge=0)
        local_rebate: float = Field(0, ge=0)
        utility_rebate: float = Field(0, ge=0)
        high_income_phase_out: bool = False

    class TCORequest(BaseModel):
        vehicle: VehicleSpecsModel
        financing: Optional[FinancingModel] = None
        energy: Optional[EnergyModel] = None
        incentives: Optional[IncentivesModel] = None
        years: int = Field(10, ge=1)

    class ComparisonRequest(BaseModel):
        ev: VehicleSpecsModel
        traditional: Optional[Dict[str, float]] = None
        hybrid: Optional[Dict[str, float]] = None
        years: int = Field(10, ge=1)
        annual_miles: float = Field(12_000, ge=0)

    class SensitivityRequest(BaseModel):
        vehicle: VehicleSpecsModel
        energy: Optional[EnergyModel] = None
        financing: Optional[FinancingModel] = None
        incentives: Optional[IncentivesModel] = None
        variable: str = Field(..., regex="^(electricity_rate|annual_miles|purchase_price|battery_cost)$")
        variation_percent: float = Field(10, gt=0)
        years: int = Field(10, ge=1)

from .finance import (
    EVComparisonAnalyzer,
    EVSensitivityAnalyzer,
    EVTotalCostOfOwnershipAnalyzer,
    EVVehicleSpecs,
    EnergyParameters,
    TaxIncentives,
    VehicleFinancing,
)


def _to_dataclass(model: Optional[Any], cls):
    if model is None:
        return None
    data = model.dict() if hasattr(model, "dict") else model
    return cls(**data)


def _ensure_router() -> APIRouter:
    if APIRouter is None:  # pragma: no cover - executed only without FastAPI installed
        raise ModuleNotFoundError(
            "FastAPI and Pydantic are required to use the API router. Install them via 'pip install fastapi pydantic'."
        )
    return APIRouter(prefix="/ev", tags=["ev_financial_model"])


ev_router = None if APIRouter is None else _ensure_router()

if ev_router is not None:  # pragma: no cover - runtime exercised in API integrations

    @ev_router.post("/tco")
    def calculate_tco(payload: TCORequest = Body(...)) -> Dict[str, Any]:
        """Calculate comprehensive TCO for a submitted EV specification."""

        vehicle = _to_dataclass(payload.vehicle, EVVehicleSpecs)
        financing = _to_dataclass(payload.financing, VehicleFinancing)
        energy = _to_dataclass(payload.energy, EnergyParameters)
        incentives = _to_dataclass(payload.incentives, TaxIncentives)

        analyzer = EVTotalCostOfOwnershipAnalyzer(
            vehicle=vehicle,
            financing=financing,
            energy_params=energy,
            incentives=incentives,
        )
        return analyzer.calculate_comprehensive_tco(years=payload.years)

    @ev_router.post("/compare")
    def compare(payload: ComparisonRequest = Body(...)) -> Dict[str, Any]:
        """Compare EV costs against traditional and hybrid alternatives."""

        vehicle = _to_dataclass(payload.ev, EVVehicleSpecs)
        analyzer = EVComparisonAnalyzer()
        return analyzer.compare_vehicles(
            ev=vehicle,
            traditional=payload.traditional,
            hybrid=payload.hybrid,
            years=payload.years,
            annual_miles=payload.annual_miles,
        )

    @ev_router.post("/sensitivity")
    def sensitivity(payload: SensitivityRequest = Body(...)) -> Dict[str, Any]:
        """Run sensitivity analysis across selected variables."""

        vehicle = _to_dataclass(payload.vehicle, EVVehicleSpecs)
        financing = _to_dataclass(payload.financing, VehicleFinancing)
        energy = _to_dataclass(payload.energy, EnergyParameters)
        incentives = _to_dataclass(payload.incentives, TaxIncentives)

        analyzer = EVTotalCostOfOwnershipAnalyzer(
            vehicle=vehicle,
            financing=financing,
            energy_params=energy,
            incentives=incentives,
        )
        sensitivity_analyzer = EVSensitivityAnalyzer(analyzer)
        try:
            return sensitivity_analyzer.sensitivity_analysis(
                variable=payload.variable,
                variation_percent=payload.variation_percent,
                years=payload.years,
            )
        except ValueError as exc:  # pragma: no cover - error handling exercised via API layer
            raise HTTPException(status_code=400, detail=str(exc)) from exc
