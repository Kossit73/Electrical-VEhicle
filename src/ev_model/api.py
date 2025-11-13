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

    class EVVehicleInput(BaseModel):
        """Input model for EV vehicle specifications."""

        name: str
        purchase_price: float = Field(gt=0, description="Purchase price in USD")
        battery_capacity_kwh: float = Field(gt=0, description="Usable battery capacity in kWh")
        epa_range_miles: float = Field(gt=0, description="EPA rated range in miles")
        efficiency_kwh_per_mile: float = Field(gt=0, description="Efficiency in kWh per mile")
        warranty_years: int = Field(ge=1, le=12, description="Battery warranty in years")
        warranty_miles: float = Field(gt=0, description="Battery warranty in miles")
        battery_replacement_cost: float = Field(gt=0, description="Battery replacement cost in USD")
        annual_registration_fee: float = Field(ge=0, description="Annual registration fee")
        annual_insurance_cost: float = Field(gt=0, description="Annual insurance cost")
        maintenance_cost_per_mile: float = Field(ge=0, description="Maintenance cost per mile")

    class VehicleFinancingInput(BaseModel):
        """Input model for vehicle financing."""

        loan_amount: float = Field(ge=0, description="Loan amount in USD")
        down_payment: float = Field(ge=0, description="Down payment in USD")
        loan_term_years: int = Field(ge=1, le=10, description="Loan term in years")
        annual_interest_rate: float = Field(ge=0, le=0.15, description="Annual interest rate as decimal")

    class EnergyParametersInput(BaseModel):
        """Input model for energy parameters."""

        electricity_rate_per_kwh: float = Field(gt=0, description="Electricity rate in $/kWh")
        home_charging_efficiency: float = Field(
            ge=0.8, le=0.95, description="Home charging efficiency"
        )
        dc_fast_charging_efficiency: float = Field(
            ge=0.75, le=0.85, description="DC fast charging efficiency"
        )
        annual_miles_driven: float = Field(gt=0, description="Annual miles driven")
        percent_home_charged: float = Field(
            ge=0, le=1, description="Percentage charged at home (0-1)"
        )
        percent_dc_charged: float = Field(
            ge=0, le=1, description="Percentage DC fast charged (0-1)"
        )
        percent_level2_charged: float = Field(
            ge=0, le=1, description="Percentage Level 2 charged (0-1)"
        )

        @validator(
            "percent_home_charged",
            "percent_dc_charged",
            "percent_level2_charged",
        )
        def _bounded(cls, value: float) -> float:
            if value < 0 or value > 1:
                raise ValueError("Charging percentages must be between 0 and 1")
            return value

        @validator("percent_level2_charged", always=True)
        def _validate_mix(cls, value: float, values: Dict[str, Any]) -> float:
            home = values.get("percent_home_charged")
            dc = values.get("percent_dc_charged")
            level2 = value

            if None not in (home, dc, level2):
                total = home + dc + level2
                if abs(total - 1.0) > 0.01:
                    raise ValueError("Charging percentages must sum to 1.0")
            return value

    class TaxIncentivesInput(BaseModel):
        """Input model for tax incentives."""

        federal_tax_credit: float = Field(
            ge=0, le=10_000, description="Federal tax credit in USD"
        )
        state_tax_credit: float = Field(ge=0, le=10_000, description="State tax credit in USD")
        local_rebate: float = Field(ge=0, le=5_000, description="Local rebate in USD")
        utility_rebate: float = Field(ge=0, le=5_000, description="Utility rebate in USD")

    class TCOCalculationRequest(BaseModel):
        """Request model for TCO calculation."""

        vehicle: EVVehicleInput
        financing: Optional[VehicleFinancingInput] = None
        energy_parameters: EnergyParametersInput
        tax_incentives: Optional[TaxIncentivesInput] = None
        years: int = Field(ge=1, le=20, default=10, description="Years to analyze")

    class ComparisonRequest(BaseModel):
        """Request model for vehicle comparison."""

        ev_vehicle: EVVehicleInput
        ev_energy_params: EnergyParametersInput
        traditional_vehicle: Optional[Dict[str, Any]] = None
        hybrid_vehicle: Optional[Dict[str, Any]] = None
        years: int = Field(ge=1, le=20, default=10, description="Years to analyze")
        annual_miles: float = Field(gt=0, default=12_000, description="Annual miles driven")

    class SensitivityRequest(BaseModel):
        """Request model for sensitivity analysis."""

        vehicle: EVVehicleInput
        energy_parameters: EnergyParametersInput
        variable: str = Field(
            description="Variable to test: electricity_rate, annual_miles, purchase_price, battery_cost"
        )
        variation_percent: float = Field(
            ge=5, le=50, default=10, description="Variation percentage"
        )
        years: int = Field(ge=1, le=20, default=10, description="Years to analyze")

        @validator("variable")
        def _validate_variable(cls, value: str) -> str:
            allowed = {
                "electricity_rate",
                "annual_miles",
                "purchase_price",
                "battery_cost",
            }
            if value not in allowed:
                raise ValueError(
                    "variable must be one of: electricity_rate, annual_miles, purchase_price, battery_cost"
                )
            return value

    class DepreciationRequest(BaseModel):
        """Request model for depreciation analysis."""

        initial_value: float = Field(gt=0, description="Initial vehicle value")
        years: int = Field(ge=1, le=20, default=10, description="Years to analyze")
        method: str = Field(
            default="market_based",
            description="Method: straight_line, declining_balance, market_based",
        )
        annual_miles: float = Field(gt=0, default=12_000, description="Annual miles driven")
        vehicle_type: str = Field(
            default="electric",
            description="Vehicle type: electric, traditional, hybrid",
        )

from .finance import (
    EVComparisonAnalyzer,
    EVSensitivityAnalyzer,
    EVTotalCostOfOwnershipAnalyzer,
    EVVehicleSpecs,
    EnergyParameters,
    TaxIncentives,
    VehicleFinancing,
    DepreciationCalculator,
    DepreciationMethod,
    DepreciationParameters,
    VehicleType,
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
    def calculate_tco(payload: TCOCalculationRequest = Body(...)) -> Dict[str, Any]:
        """Calculate comprehensive TCO for a submitted EV specification."""

        vehicle = _to_dataclass(payload.vehicle, EVVehicleSpecs)
        financing = _to_dataclass(payload.financing, VehicleFinancing)
        energy = _to_dataclass(payload.energy_parameters, EnergyParameters)
        incentives = _to_dataclass(payload.tax_incentives, TaxIncentives)

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

        vehicle = _to_dataclass(payload.ev_vehicle, EVVehicleSpecs)
        energy_params = _to_dataclass(payload.ev_energy_params, EnergyParameters)
        analyzer = EVComparisonAnalyzer()
        return analyzer.compare_vehicles(
            ev=vehicle,
            traditional=payload.traditional_vehicle,
            hybrid=payload.hybrid_vehicle,
            years=payload.years,
            annual_miles=payload.annual_miles,
            energy_params=energy_params,
        )

    @ev_router.post("/sensitivity")
    def sensitivity(payload: SensitivityRequest = Body(...)) -> Dict[str, Any]:
        """Run sensitivity analysis across selected variables."""

        vehicle = _to_dataclass(payload.vehicle, EVVehicleSpecs)
        energy = _to_dataclass(payload.energy_parameters, EnergyParameters)

        analyzer = EVTotalCostOfOwnershipAnalyzer(
            vehicle=vehicle,
            energy_params=energy,
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

    @ev_router.post("/depreciation")
    def depreciation(payload: DepreciationRequest = Body(...)) -> Dict[str, Any]:
        """Generate a depreciation schedule using the requested method."""

        try:
            method = DepreciationMethod(payload.method)
        except ValueError as exc:  # pragma: no cover - error handling exercised via API layer
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        try:
            vehicle_type = VehicleType(payload.vehicle_type)
        except ValueError as exc:  # pragma: no cover - error handling exercised via API layer
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        params = DepreciationParameters(
            method=method,
            useful_life_years=payload.years,
            annual_miles=payload.annual_miles,
        )
        calculator = DepreciationCalculator(
            purchase_price=payload.initial_value,
            params=params,
            vehicle_type=vehicle_type,
        )
        schedule = calculator.calculate_depreciation(
            initial_value=payload.initial_value,
            years=payload.years,
            method=method,
            annual_miles=payload.annual_miles,
        )

        return {
            "method": method.value,
            "vehicle_type": vehicle_type.value,
            "schedule": schedule.to_dict("records"),
        }
