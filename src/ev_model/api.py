"""FastAPI router exposing EV financial modelling endpoints."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

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
        def validate_percentages_sum(cls, value: float, values: Dict[str, Any]) -> float:
            """Validate that charging percentages total 100%."""

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

    class TCOSummary(BaseModel):
        """TCO Summary response."""

        vehicle_name: str
        initial_cost: float
        net_initial_cost: float
        total_incentives: float
        total_ownership_cost: float
        total_miles_driven: float
        final_residual_value: float
        net_ownership_cost: float
        cost_per_mile: float

    class TCOCalculationResponse(BaseModel):
        """TCO Calculation response."""

        status: str
        summary: TCOSummary
        annual_breakdown: List[Dict[str, Any]]
        operating_details: List[Dict[str, Any]]
        energy_details: List[Dict[str, Any]]
        depreciation_details: List[Dict[str, Any]]

    class ComparisonResult(BaseModel):
        """Comparison result response."""

        status: str
        ev_cost: float
        alternative_cost: float
        total_savings: float
        annual_savings: float
        payback_period_years: Optional[float]
        savings_percent: float

    class SensitivityScenario(BaseModel):
        """Sensitivity analysis scenario."""

        factor: float
        change_percent: float
        new_value: float
        cost_per_mile: float
        impact_percent: float

    class SensitivityResponse(BaseModel):
        """Sensitivity analysis response."""

        status: str
        variable: str
        base_cost_per_mile: float
        scenarios: List[SensitivityScenario]

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


logger = logging.getLogger(__name__)

ev_router = None if APIRouter is None else _ensure_router()

if ev_router is not None:  # pragma: no cover - runtime exercised in API integrations

    def _build_tco_response(
        payload: TCOCalculationRequest,
    ) -> TCOCalculationResponse:
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

        tco = analyzer.calculate_comprehensive_tco(years=payload.years)

        return TCOCalculationResponse(
            status="success",
            summary=TCOSummary(**tco["summary"]),
            annual_breakdown=tco["annual_details"],
            operating_details=tco["operating_details"],
            energy_details=tco["energy_details"],
            depreciation_details=tco["depreciation_details"],
        )

    @ev_router.post("/calculate-tco", response_model=TCOCalculationResponse)
    def calculate_ev_tco(
        request: TCOCalculationRequest,
    ) -> TCOCalculationResponse:
        try:
            return _build_tco_response(request)
        except Exception as exc:  # pragma: no cover - runtime error propagation
            logger.error("Error calculating EV TCO: %s", exc)
            raise HTTPException(status_code=500, detail=f"Error calculating TCO: {exc}") from exc

    @ev_router.post("/tco")
    def calculate_tco(payload: TCOCalculationRequest = Body(...)) -> Dict[str, Any]:
        """Deprecated helper retaining backwards compatible endpoint."""

        response = _build_tco_response(payload)
        return {
            "summary": response.summary.dict(),
            "annual_details": response.annual_breakdown,
            "operating_details": response.operating_details,
            "energy_details": response.energy_details,
            "depreciation_details": response.depreciation_details,
        }

    @ev_router.post("/compare-vehicles")
    def compare_vehicles(request: ComparisonRequest) -> Dict[str, Any]:
        try:
            vehicle = _to_dataclass(request.ev_vehicle, EVVehicleSpecs)
            energy_params = _to_dataclass(request.ev_energy_params, EnergyParameters)
            analyzer = EVComparisonAnalyzer()
            comparison = analyzer.compare_vehicles(
                ev=vehicle,
                traditional=request.traditional_vehicle,
                hybrid=request.hybrid_vehicle,
                years=request.years,
                annual_miles=request.annual_miles,
                energy_params=energy_params,
            )

            response: Dict[str, Any] = {"status": "success", "comparison": comparison}

            if "ev_vs_traditional" in comparison and "traditional" in comparison:
                response["ev_vs_traditional"] = ComparisonResult(
                    status="success",
                    ev_cost=comparison["ev"]["net_ownership_cost"],
                    alternative_cost=comparison["traditional"]["net_cost"],
                    total_savings=comparison["ev_vs_traditional"]["total_savings"],
                    annual_savings=comparison["ev_vs_traditional"]["annual_savings"],
                    payback_period_years=comparison["ev_vs_traditional"].get(
                        "payback_period_years"
                    ),
                    savings_percent=comparison["ev_vs_traditional"]["savings_percent"],
                ).dict()

            if "ev_vs_hybrid" in comparison and "hybrid" in comparison:
                response["ev_vs_hybrid"] = ComparisonResult(
                    status="success",
                    ev_cost=comparison["ev"]["net_ownership_cost"],
                    alternative_cost=comparison["hybrid"]["net_cost"],
                    total_savings=comparison["ev_vs_hybrid"]["total_savings"],
                    annual_savings=comparison["ev_vs_hybrid"]["annual_savings"],
                    payback_period_years=comparison["ev_vs_hybrid"].get(
                        "payback_period_years"
                    ),
                    savings_percent=comparison["ev_vs_hybrid"]["savings_percent"],
                ).dict()

            return response
        except Exception as exc:  # pragma: no cover - runtime error propagation
            logger.error("Error comparing vehicles: %s", exc)
            raise HTTPException(status_code=500, detail=f"Error comparing vehicles: {exc}") from exc

    @ev_router.post("/compare")
    def compare(payload: ComparisonRequest = Body(...)) -> Dict[str, Any]:
        comparison_response = compare_vehicles(payload)
        return comparison_response["comparison"]

    @ev_router.post("/sensitivity-analysis", response_model=SensitivityResponse)
    def run_sensitivity_analysis(
        request: SensitivityRequest,
    ) -> SensitivityResponse:
        try:
            vehicle = _to_dataclass(request.vehicle, EVVehicleSpecs)
            energy = _to_dataclass(request.energy_parameters, EnergyParameters)

            analyzer = EVTotalCostOfOwnershipAnalyzer(
                vehicle=vehicle,
                energy_params=energy,
            )
            sensitivity_analyzer = EVSensitivityAnalyzer(analyzer)

            result = sensitivity_analyzer.sensitivity_analysis(
                variable=request.variable,
                variation_percent=request.variation_percent,
                years=request.years,
            )

            return SensitivityResponse(
                status="success",
                variable=result["variable"],
                base_cost_per_mile=result["base_cost_per_mile"],
                scenarios=[SensitivityScenario(**scenario) for scenario in result["scenarios"]],
            )
        except ValueError as exc:  # pragma: no cover - validation triggered by analyzer
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:  # pragma: no cover - runtime error propagation
            logger.error("Error in sensitivity analysis: %s", exc)
            raise HTTPException(status_code=500, detail=f"Error in sensitivity analysis: {exc}") from exc

    @ev_router.post("/sensitivity")
    def sensitivity(payload: SensitivityRequest = Body(...)) -> Dict[str, Any]:
        response = run_sensitivity_analysis(payload)
        return {
            "variable": response.variable,
            "base_cost_per_mile": response.base_cost_per_mile,
            "scenarios": [scenario.dict() for scenario in response.scenarios],
        }

    @ev_router.post("/depreciation-schedule")
    def get_depreciation_schedule(
        request: DepreciationRequest,
    ) -> Dict[str, Any]:
        try:
            vehicle_type = VehicleType(request.vehicle_type)
            depreciation_method = DepreciationMethod(request.method)
        except ValueError as exc:  # pragma: no cover - invalid enum mapping
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        try:
            calculator = DepreciationCalculator(vehicle_type)
            depreciation_df = calculator.calculate_depreciation(
                initial_value=request.initial_value,
                years=request.years,
                method=depreciation_method,
                annual_miles=request.annual_miles,
            )
        except Exception as exc:  # pragma: no cover - runtime error propagation
            logger.error("Error calculating depreciation: %s", exc)
            raise HTTPException(status_code=500, detail=f"Error calculating depreciation: {exc}") from exc

        return {
            "status": "success",
            "method": request.method,
            "depreciation_schedule": depreciation_df.to_dict("records"),
        }

    @ev_router.post("/depreciation")
    def depreciation(payload: DepreciationRequest = Body(...)) -> Dict[str, Any]:
        return get_depreciation_schedule(payload)

    @ev_router.get("/sample-vehicles")
    def get_sample_vehicles() -> Dict[str, Any]:
        return {
            "status": "success",
            "vehicles": {
                "tesla_model_3": {
                    "name": "Tesla Model 3 (Standard Range Plus)",
                    "purchase_price": 46_995,
                    "battery_capacity_kwh": 54,
                    "epa_range_miles": 263,
                    "efficiency_kwh_per_mile": 0.205,
                    "warranty_years": 8,
                    "warranty_miles": 120_000,
                    "battery_replacement_cost": 7_000,
                    "annual_registration_fee": 250,
                    "annual_insurance_cost": 1_200,
                    "maintenance_cost_per_mile": 0.02,
                },
                "chevy_bolt": {
                    "name": "Chevrolet Bolt EV",
                    "purchase_price": 42_000,
                    "battery_capacity_kwh": 65,
                    "epa_range_miles": 260,
                    "efficiency_kwh_per_mile": 0.210,
                    "warranty_years": 8,
                    "warranty_miles": 100_000,
                    "battery_replacement_cost": 6_000,
                    "annual_registration_fee": 180,
                    "annual_insurance_cost": 1_100,
                    "maintenance_cost_per_mile": 0.015,
                },
                "nissan_leaf": {
                    "name": "Nissan Leaf (SV Plus)",
                    "purchase_price": 35_850,
                    "battery_capacity_kwh": 62,
                    "epa_range_miles": 226,
                    "efficiency_kwh_per_mile": 0.230,
                    "warranty_years": 8,
                    "warranty_miles": 100_000,
                    "battery_replacement_cost": 5_500,
                    "annual_registration_fee": 200,
                    "annual_insurance_cost": 1_050,
                    "maintenance_cost_per_mile": 0.018,
                },
            },
        }

    @ev_router.get("/regional-rates")
    def get_regional_electricity_rates() -> Dict[str, Any]:
        return {
            "status": "success",
            "regions": {
                "california": {
                    "electricity_rate_per_kwh": 0.18,
                    "description": "High electricity costs",
                },
                "texas": {
                    "electricity_rate_per_kwh": 0.11,
                    "description": "Lower electricity costs",
                },
                "new_york": {
                    "electricity_rate_per_kwh": 0.16,
                    "description": "Moderate-to-high electricity costs",
                },
                "florida": {
                    "electricity_rate_per_kwh": 0.12,
                    "description": "Lower-moderate electricity costs",
                },
                "washington": {
                    "electricity_rate_per_kwh": 0.10,
                    "description": "Lowest electricity costs (hydropower)",
                },
            },
        }
