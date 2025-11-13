"""
Legacy Electric Vehicle (EV) Financial Model implementation.

This module mirrors the step-by-step example implementation provided by the
client. It intentionally keeps the structure and comments of the shared code so
that documentation, tutorials, or notebooks referencing that snippet can import
it without modification while we continue to evolve the richer finance API in
``ev_model.finance``.
"""

from __future__ import annotations

import logging
import warnings
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

try:  # pragma: no cover - optional dependency
    import pandas as pd
except ModuleNotFoundError:  # pragma: no cover - reuse the lightweight fallback
    from .finance import pd  # type: ignore

# The reference implementation silences numerical optimisation warnings so we
# preserve the behaviour for parity with the supplied code sample.
warnings.filterwarnings("ignore")

logger = logging.getLogger(__name__)


class DepreciationMethod(Enum):
    """Depreciation calculation methods for vehicles."""

    STRAIGHT_LINE = "straight_line"
    DECLINING_BALANCE = "declining_balance"
    MARKET_BASED = "market_based"


class VehicleType(Enum):
    """Vehicle type classifications."""

    ELECTRIC = "electric"
    TRADITIONAL = "traditional"
    HYBRID = "hybrid"


@dataclass
class EVVehicleSpecs:
    """Specifications for an electric vehicle."""

    name: str
    purchase_price: float
    battery_capacity_kwh: float  # Usable battery capacity
    epa_range_miles: float
    efficiency_kwh_per_mile: float
    warranty_years: int
    warranty_miles: float
    battery_replacement_cost: float
    annual_registration_fee: float
    annual_insurance_cost: float
    maintenance_cost_per_mile: float  # Typically lower for EVs


@dataclass
class VehicleFinancing:
    """Vehicle financing parameters."""

    loan_amount: float
    down_payment: float
    loan_term_years: int
    annual_interest_rate: float
    monthly_payment: Optional[float] = None


@dataclass
class EnergyParameters:
    """Energy consumption and cost parameters."""

    electricity_rate_per_kwh: float  # $/kWh
    home_charging_efficiency: float  # 0.85-0.95 typical
    dc_fast_charging_efficiency: float  # 0.75-0.85 typical
    annual_miles_driven: float
    percent_home_charged: float  # 0-1
    percent_dc_charged: float  # 0-1
    percent_level2_charged: float  # 0-1


@dataclass
class TaxIncentives:
    """Tax incentives and rebates for EVs."""

    federal_tax_credit: float
    state_tax_credit: float
    local_rebate: float
    utility_rebate: float
    high_income_phase_out: bool = False


class EVAcquisitionCalculator:
    """Calculate vehicle acquisition costs including financing and incentives."""

    def __init__(self, vehicle: EVVehicleSpecs, financing: Optional[VehicleFinancing] = None):
        self.vehicle = vehicle
        self.financing = financing or VehicleFinancing(
            loan_amount=vehicle.purchase_price * 0.8,
            down_payment=vehicle.purchase_price * 0.2,
            loan_term_years=5,
            annual_interest_rate=0.045,
        )
        self._calculate_monthly_payment()

    def _calculate_monthly_payment(self) -> None:
        """Calculate monthly loan payment using standard amortization."""

        r = self.financing.annual_interest_rate / 12
        n = self.financing.loan_term_years * 12
        if r > 0:
            payment = self.financing.loan_amount * (r * (1 + r) ** n) / ((1 + r) ** n - 1)
        else:
            payment = self.financing.loan_amount / n
        self.financing.monthly_payment = payment

    def get_total_acquisition_cost(self, incentives: Optional[TaxIncentives] = None) -> Dict[str, float]:
        """Calculate total acquisition cost including financing and incentives."""

        total_incentives = 0
        if incentives:
            total_incentives = (
                incentives.federal_tax_credit
                + incentives.state_tax_credit
                + incentives.local_rebate
                + incentives.utility_rebate
            )

        net_cost = self.vehicle.purchase_price - total_incentives

        return {
            "purchase_price": self.vehicle.purchase_price,
            "registration_fee_year1": self.vehicle.annual_registration_fee,
            "insurance_year1": self.vehicle.annual_insurance_cost,
            "federal_tax_credit": incentives.federal_tax_credit if incentives else 0,
            "state_tax_credit": incentives.state_tax_credit if incentives else 0,
            "local_rebate": incentives.local_rebate if incentives else 0,
            "utility_rebate": incentives.utility_rebate if incentives else 0,
            "total_incentives": total_incentives,
            "net_purchase_cost": net_cost,
            "monthly_payment": self.financing.monthly_payment,
            "total_financed_amount": self.financing.monthly_payment * self.financing.loan_term_years * 12,
        }


class EVOperatingCostsCalculator:
    """Calculate operating costs for electric vehicles."""

    def __init__(self, vehicle: EVVehicleSpecs):
        self.vehicle = vehicle

    def calculate_annual_operating_costs(
        self,
        annual_miles: float,
        annual_registration: Optional[float] = None,
        annual_insurance: Optional[float] = None,
        maintenance_inflation_rate: float = 0.02,
        years: int = 10,
    ) -> pd.DataFrame:
        """Calculate year-by-year operating costs."""

        results: List[Dict[str, float]] = []
        registration_fee = annual_registration or self.vehicle.annual_registration_fee
        insurance_cost = annual_insurance or self.vehicle.annual_insurance_cost

        for year in range(1, years + 1):
            year_miles = annual_miles * year

            maintenance_cost = (
                self.vehicle.maintenance_cost_per_mile
                * annual_miles
                * (1 + maintenance_inflation_rate) ** (year - 1)
            )

            battery_degradation_cost = self._calculate_battery_costs(year, annual_miles)

            registration = registration_fee * (1.02 ** (year - 1))
            insurance = insurance_cost * (1.015 ** (year - 1))

            tire_cost = self._calculate_tire_replacement_cost(year, annual_miles)

            total_operating = (
                maintenance_cost
                + battery_degradation_cost
                + registration
                + insurance
                + tire_cost
            )

            results.append(
                {
                    "year": year,
                    "annual_miles": annual_miles,
                    "cumulative_miles": year_miles,
                    "maintenance_cost": maintenance_cost,
                    "battery_cost": battery_degradation_cost,
                    "registration_fee": registration,
                    "insurance_cost": insurance,
                    "tire_replacement": tire_cost,
                    "total_operating_cost": total_operating,
                }
            )

        return pd.DataFrame(results)

    def _calculate_battery_costs(self, year: int, annual_miles: float) -> float:
        """Calculate battery-related costs including degradation monitoring."""

        if year <= self.vehicle.warranty_years:
            return 0

        years_past_warranty = year - self.vehicle.warranty_years
        battery_cost = self.vehicle.battery_replacement_cost * 0.05 * years_past_warranty
        return max(0, battery_cost)

    def _calculate_tire_replacement_cost(self, year: int, annual_miles: float) -> float:
        """Calculate tire replacement costs."""

        cumulative_miles = annual_miles * year
        tire_life_miles = 50_000
        tire_replacement_cost = 150

        num_replacements = int(cumulative_miles / tire_life_miles)
        return max(0, num_replacements * tire_replacement_cost * 4)


class EVEnergyCostsCalculator:
    """Calculate energy costs for electric vehicles."""

    def __init__(self, vehicle: EVVehicleSpecs, energy_params: EnergyParameters):
        self.vehicle = vehicle
        self.energy_params = energy_params

    def calculate_annual_energy_cost(self, years: int = 10) -> pd.DataFrame:
        """Calculate annual energy costs including different charging methods."""

        results: List[Dict[str, float]] = []

        for year in range(1, years + 1):
            annual_miles = self.energy_params.annual_miles_driven
            total_kwh_needed = annual_miles * self.vehicle.efficiency_kwh_per_mile

            home_kwh = (
                total_kwh_needed
                * self.energy_params.percent_home_charged
                / self.energy_params.home_charging_efficiency
            )
            dc_kwh = (
                total_kwh_needed
                * self.energy_params.percent_dc_charged
                / self.energy_params.dc_fast_charging_efficiency
            )
            level2_kwh = (
                total_kwh_needed
                * self.energy_params.percent_level2_charged
                / self.energy_params.home_charging_efficiency
            )

            home_cost = home_kwh * self.energy_params.electricity_rate_per_kwh
            dc_cost = dc_kwh * self.energy_params.electricity_rate_per_kwh * 1.45
            level2_cost = level2_kwh * self.energy_params.electricity_rate_per_kwh

            total_energy_cost = home_cost + dc_cost + level2_cost
            cost_per_mile = total_energy_cost / annual_miles if annual_miles > 0 else 0

            results.append(
                {
                    "year": year,
                    "annual_miles": annual_miles,
                    "total_kwh": total_kwh_needed,
                    "home_kwh": home_kwh,
                    "dc_kwh": dc_kwh,
                    "level2_kwh": level2_kwh,
                    "home_charging_cost": home_cost,
                    "dc_charging_cost": dc_cost,
                    "level2_charging_cost": level2_cost,
                    "total_energy_cost": total_energy_cost,
                    "cost_per_mile": cost_per_mile,
                }
            )

        return pd.DataFrame(results)


class DepreciationCalculator:
    """Calculate vehicle depreciation using various methods."""

    def __init__(self, vehicle_type: VehicleType = VehicleType.ELECTRIC):
        self.vehicle_type = vehicle_type

    def calculate_depreciation(
        self,
        initial_value: float,
        years: int = 10,
        method: DepreciationMethod = DepreciationMethod.MARKET_BASED,
        annual_miles: float = 12_000,
    ) -> pd.DataFrame:
        """Calculate depreciation using specified method."""

        if method == DepreciationMethod.STRAIGHT_LINE:
            return self._straight_line_depreciation(initial_value, years)
        if method == DepreciationMethod.DECLINING_BALANCE:
            return self._declining_balance_depreciation(initial_value, years)
        return self._market_based_depreciation(initial_value, years, annual_miles)

    def _straight_line_depreciation(self, initial_value: float, years: int) -> pd.DataFrame:
        """Straight-line depreciation: equal annual reduction."""

        results: List[Dict[str, float]] = []
        annual_depreciation = initial_value / (years + 1)

        for year in range(1, years + 1):
            book_value = initial_value - (annual_depreciation * year)
            results.append(
                {
                    "year": year,
                    "depreciation_amount": annual_depreciation,
                    "cumulative_depreciation": annual_depreciation * year,
                    "book_value": book_value,
                    "residual_value_percent": (book_value / initial_value) * 100,
                }
            )

        return pd.DataFrame(results)

    def _declining_balance_depreciation(self, initial_value: float, years: int) -> pd.DataFrame:
        """Double declining balance depreciation: faster initial depreciation."""

        results: List[Dict[str, float]] = []
        rate = 2 / (years + 1)
        book_value = initial_value
        cumulative_depreciation = 0

        for year in range(1, years + 1):
            annual_depreciation = book_value * rate
            cumulative_depreciation += annual_depreciation
            book_value -= annual_depreciation

            results.append(
                {
                    "year": year,
                    "depreciation_amount": annual_depreciation,
                    "cumulative_depreciation": cumulative_depreciation,
                    "book_value": max(0, book_value),
                    "residual_value_percent": max(0, (book_value / initial_value) * 100),
                }
            )

        return pd.DataFrame(results)

    def _market_based_depreciation(self, initial_value: float, years: int, annual_miles: float) -> pd.DataFrame:
        """Market-based depreciation using empirical EV depreciation curves."""

        results: List[Dict[str, float]] = []
        book_value = initial_value
        cumulative_depreciation = 0

        depreciation_schedule = {
            1: 0.18,
            2: 0.10,
            3: 0.10,
            4: 0.08,
            5: 0.08,
            6: 0.06,
            7: 0.05,
            8: 0.05,
            9: 0.04,
            10: 0.04,
        }

        for year in range(1, years + 1):
            rate = depreciation_schedule.get(year, 0.03)
            annual_depreciation = book_value * rate
            cumulative_depreciation += annual_depreciation
            book_value -= annual_depreciation

            cumulative_miles = annual_miles * year
            if cumulative_miles > 150_000:
                book_value *= 1 - (cumulative_miles - 150_000) / 1_000_000 * 0.05

            results.append(
                {
                    "year": year,
                    "depreciation_amount": annual_depreciation,
                    "cumulative_depreciation": cumulative_depreciation,
                    "book_value": max(0, book_value),
                    "residual_value_percent": max(0, (book_value / initial_value) * 100),
                }
            )

        return pd.DataFrame(results)


class EVTotalCostOfOwnershipAnalyzer:
    """Comprehensive TCO analysis for electric vehicles."""

    def __init__(
        self,
        vehicle: EVVehicleSpecs,
        financing: Optional[VehicleFinancing] = None,
        energy_params: Optional[EnergyParameters] = None,
        incentives: Optional[TaxIncentives] = None,
    ):
        self.vehicle = vehicle
        self.financing = financing
        self.energy_params = energy_params or EnergyParameters(
            electricity_rate_per_kwh=0.14,
            home_charging_efficiency=0.90,
            dc_fast_charging_efficiency=0.80,
            annual_miles_driven=12_000,
            percent_home_charged=0.7,
            percent_dc_charged=0.1,
            percent_level2_charged=0.2,
        )
        self.incentives = incentives

        self.acquisition_calc = EVAcquisitionCalculator(vehicle, financing)
        self.operating_calc = EVOperatingCostsCalculator(vehicle)
        self.energy_calc = EVEnergyCostsCalculator(vehicle, self.energy_params)
        self.depreciation_calc = DepreciationCalculator(VehicleType.ELECTRIC)

    def calculate_comprehensive_tco(self, years: int = 10) -> Dict[str, Any]:
        """Calculate comprehensive total cost of ownership."""

        acquisition = self.acquisition_calc.get_total_acquisition_cost(self.incentives)

        operating_df = self.operating_calc.calculate_annual_operating_costs(
            annual_miles=self.energy_params.annual_miles_driven,
            years=years,
        )

        energy_df = self.energy_calc.calculate_annual_energy_cost(years=years)

        depreciation_df = self.depreciation_calc.calculate_depreciation(
            initial_value=acquisition["net_purchase_cost"],
            years=years,
            method=DepreciationMethod.MARKET_BASED,
            annual_miles=self.energy_params.annual_miles_driven,
        )

        tco_df = pd.DataFrame(
            {
                "year": operating_df["year"],
                "financing_cost": self.acquisition_calc.financing.monthly_payment * 12,
                "operating_cost": operating_df["total_operating_cost"],
                "energy_cost": energy_df["total_energy_cost"],
                "cumulative_financing": self.acquisition_calc.financing.monthly_payment
                * 12
                * operating_df["year"],
            }
        )

        tco_df["total_annual_cost"] = (
            tco_df["financing_cost"] + tco_df["operating_cost"] + tco_df["energy_cost"]
        )
        tco_df["cumulative_cost"] = tco_df["total_annual_cost"].cumsum()
        tco_df["residual_value"] = depreciation_df["book_value"].values
        tco_df["net_cost_after_residual"] = tco_df["cumulative_cost"] - tco_df["residual_value"]
        tco_df["cumulative_miles"] = self.energy_params.annual_miles_driven * tco_df["year"]
        tco_df["cost_per_mile"] = tco_df["cumulative_cost"] / tco_df["cumulative_miles"]

        total_cost = tco_df["total_annual_cost"].sum()
        total_miles = tco_df["cumulative_miles"].iloc[-1]
        final_residual = tco_df["residual_value"].iloc[-1]
        net_cost = total_cost - final_residual

        summary = {
            "vehicle_name": self.vehicle.name,
            "initial_cost": acquisition["purchase_price"],
            "net_initial_cost": acquisition["net_purchase_cost"],
            "total_incentives": acquisition["total_incentives"],
            "total_ownership_cost": total_cost,
            "total_miles_driven": total_miles,
            "final_residual_value": final_residual,
            "net_ownership_cost": net_cost,
            "cost_per_mile": net_cost / total_miles if total_miles > 0 else 0,
            "financing_years": self.financing.loan_term_years if self.financing else 0,
            "financing_interest_rate": self.financing.annual_interest_rate if self.financing else 0,
        }

        return {
            "acquisition": acquisition,
            "annual_details": tco_df.to_dict("records"),
            "operating_details": operating_df.to_dict("records"),
            "energy_details": energy_df.to_dict("records"),
            "depreciation_details": depreciation_df.to_dict("records"),
            "summary": summary,
        }


class EVComparisonAnalyzer:
    """Compare EV TCO with traditional and hybrid vehicles."""

    def compare_vehicles(
        self,
        ev: EVVehicleSpecs,
        traditional: Optional[Dict[str, float]] = None,
        hybrid: Optional[Dict[str, float]] = None,
        years: int = 10,
        annual_miles: float = 12_000,
    ) -> Dict[str, Any]:
        """Compare TCO across vehicle types."""

        ev_energy_params = EnergyParameters(
            electricity_rate_per_kwh=0.14,
            home_charging_efficiency=0.90,
            dc_fast_charging_efficiency=0.80,
            annual_miles_driven=annual_miles,
            percent_home_charged=0.7,
            percent_dc_charged=0.1,
            percent_level2_charged=0.2,
        )

        ev_analyzer = EVTotalCostOfOwnershipAnalyzer(vehicle=ev, energy_params=ev_energy_params)
        ev_tco = ev_analyzer.calculate_comprehensive_tco(years=years)

        comparison: Dict[str, Any] = {
            "ev": ev_tco["summary"],
            "vehicles_compared": {
                "EV": ev.name,
                "Traditional": traditional.get("name", "N/A") if traditional else None,
                "Hybrid": hybrid.get("name", "N/A") if hybrid else None,
            },
            "years_analyzed": years,
            "annual_miles": annual_miles,
        }

        if traditional:
            comparison["traditional"] = self._calculate_traditional_vehicle_tco(
                traditional, years, annual_miles
            )
            comparison["ev_vs_traditional"] = self._calculate_savings(
                ev_tco["summary"]["net_ownership_cost"],
                comparison["traditional"]["net_cost"],
                ev_tco["summary"]["initial_cost"],
                traditional["initial_cost"],
                years,
            )

        if hybrid:
            comparison["hybrid"] = self._calculate_hybrid_vehicle_tco(hybrid, years, annual_miles)
            comparison["ev_vs_hybrid"] = self._calculate_savings(
                ev_tco["summary"]["net_ownership_cost"],
                comparison["hybrid"]["net_cost"],
                ev_tco["summary"]["initial_cost"],
                hybrid["initial_cost"],
                years,
            )

        return comparison

    def _calculate_traditional_vehicle_tco(
        self,
        vehicle: Dict[str, float],
        years: int,
        annual_miles: float,
    ) -> Dict[str, float]:
        """Calculate TCO for traditional gasoline vehicle."""

        annual_fuel_cost = (annual_miles / vehicle.get("mpg", 25)) * vehicle.get("fuel_price", 3.5)
        maintenance_cost = annual_miles * vehicle.get("maintenance_per_mile", 0.08)
        annual_insurance = vehicle.get("insurance_per_year", 1200)
        annual_registration = vehicle.get("registration_per_year", 200)

        annual_cost = (
            annual_fuel_cost + maintenance_cost + annual_insurance + annual_registration
        )

        financing_cost = vehicle.get("monthly_payment", 400) * 12 * 6
        total_cost = (annual_cost * years) + financing_cost
        residual_value = vehicle.get("initial_cost", 30_000) * 0.4

        return {
            "annual_fuel_cost": annual_fuel_cost,
            "annual_maintenance": maintenance_cost,
            "annual_insurance": annual_insurance,
            "annual_registration": annual_registration,
            "total_annual_cost": annual_cost,
            "total_cost": total_cost,
            "residual_value": residual_value,
            "net_cost": total_cost - residual_value,
        }

    def _calculate_hybrid_vehicle_tco(
        self,
        vehicle: Dict[str, float],
        years: int,
        annual_miles: float,
    ) -> Dict[str, float]:
        """Calculate TCO for hybrid vehicle."""

        annual_fuel_cost = (annual_miles / vehicle.get("mpg_combined", 50)) * vehicle.get(
            "fuel_price", 3.5
        )
        maintenance_cost = annual_miles * vehicle.get("maintenance_per_mile", 0.05)
        annual_insurance = vehicle.get("insurance_per_year", 1300)
        annual_registration = vehicle.get("registration_per_year", 200)

        annual_cost = (
            annual_fuel_cost + maintenance_cost + annual_insurance + annual_registration
        )

        financing_cost = vehicle.get("monthly_payment", 500) * 12 * 6
        total_cost = (annual_cost * years) + financing_cost
        residual_value = vehicle.get("initial_cost", 35_000) * 0.45

        return {
            "annual_fuel_cost": annual_fuel_cost,
            "annual_maintenance": maintenance_cost,
            "annual_insurance": annual_insurance,
            "annual_registration": annual_registration,
            "total_annual_cost": annual_cost,
            "total_cost": total_cost,
            "residual_value": residual_value,
            "net_cost": total_cost - residual_value,
        }

    def _calculate_savings(
        self,
        ev_cost: float,
        alternative_cost: float,
        ev_purchase_price: float,
        alternative_price: float,
        years: int,
    ) -> Dict[str, Any]:
        """Calculate savings and payback period."""

        annual_savings = (alternative_cost - ev_cost) / years
        total_savings = alternative_cost - ev_cost
        price_premium = ev_purchase_price - alternative_price

        if annual_savings > 0:
            payback_years = min(years, price_premium / annual_savings)
        else:
            payback_years = None

        return {
            "total_savings": total_savings,
            "annual_savings": annual_savings,
            "price_premium": price_premium,
            "payback_period_years": payback_years,
            "savings_percent": (total_savings / alternative_cost) * 100 if alternative_cost > 0 else 0,
        }


class EVSensitivityAnalyzer:
    """Perform sensitivity analysis on EV financial model."""

    def __init__(self, base_tco_analysis: EVTotalCostOfOwnershipAnalyzer):
        self.base_analyzer = base_tco_analysis

    def sensitivity_analysis(
        self,
        variable: str,
        variation_percent: float = 10,
        years: int = 10,
    ) -> Dict[str, Any]:
        """Perform sensitivity analysis on key variables."""

        base_tco = self.base_analyzer.calculate_comprehensive_tco(years=years)
        base_cost_per_mile = base_tco["summary"]["cost_per_mile"]

        results: Dict[str, Any] = {
            "variable": variable,
            "base_value": self._get_variable_value(variable),
            "base_cost_per_mile": base_cost_per_mile,
            "scenarios": [],
        }

        for factor in [0.8, 0.9, 1.0, 1.1, 1.2]:
            modified_analyzer = self._create_modified_analyzer(variable, factor)
            modified_tco = modified_analyzer.calculate_comprehensive_tco(years=years)

            change_percent = (factor - 1) * 100
            cost_impact = modified_tco["summary"]["cost_per_mile"] - base_cost_per_mile

            results["scenarios"].append(
                {
                    "factor": factor,
                    "change_percent": change_percent,
                    "new_value": self._get_variable_value(variable, factor),
                    "cost_per_mile": modified_tco["summary"]["cost_per_mile"],
                    "cost_impact": cost_impact,
                    "impact_percent": (cost_impact / base_cost_per_mile * 100)
                    if base_cost_per_mile != 0
                    else 0,
                }
            )

        return results

    def _get_variable_value(self, variable: str, factor: float = 1.0) -> float:
        """Get current value of a variable."""

        if variable == "electricity_rate":
            return self.base_analyzer.energy_params.electricity_rate_per_kwh * factor
        if variable == "annual_miles":
            return self.base_analyzer.energy_params.annual_miles_driven * factor
        if variable == "purchase_price":
            return self.base_analyzer.vehicle.purchase_price * factor
        if variable == "battery_cost":
            return self.base_analyzer.vehicle.battery_replacement_cost * factor
        return 0

    def _create_modified_analyzer(self, variable: str, factor: float) -> EVTotalCostOfOwnershipAnalyzer:
        """Create a modified analyzer with changed variable."""

        energy_params = EnergyParameters(
            electricity_rate_per_kwh=self.base_analyzer.energy_params.electricity_rate_per_kwh,
            home_charging_efficiency=self.base_analyzer.energy_params.home_charging_efficiency,
            dc_fast_charging_efficiency=self.base_analyzer.energy_params.dc_fast_charging_efficiency,
            annual_miles_driven=self.base_analyzer.energy_params.annual_miles_driven,
            percent_home_charged=self.base_analyzer.energy_params.percent_home_charged,
            percent_dc_charged=self.base_analyzer.energy_params.percent_dc_charged,
            percent_level2_charged=self.base_analyzer.energy_params.percent_level2_charged,
        )

        vehicle = EVVehicleSpecs(
            **{**self.base_analyzer.vehicle.__dict__}  # shallow copy of dataclass fields
        )

        if variable == "electricity_rate":
            energy_params.electricity_rate_per_kwh *= factor
        elif variable == "annual_miles":
            energy_params.annual_miles_driven *= factor
        elif variable == "purchase_price":
            vehicle.purchase_price *= factor
        elif variable == "battery_cost":
            vehicle.battery_replacement_cost *= factor

        return EVTotalCostOfOwnershipAnalyzer(
            vehicle=vehicle,
            financing=self.base_analyzer.financing,
            energy_params=energy_params,
            incentives=self.base_analyzer.incentives,
        )
