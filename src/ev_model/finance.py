"""Comprehensive tools for analysing EV ownership costs."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional


logger = logging.getLogger(__name__)


class DepreciationMethod(Enum):
    """Supported depreciation calculation methodologies."""

    STRAIGHT_LINE = "straight_line"
    DECLINING_BALANCE = "declining_balance"
    MARKET_BASED = "market_based"


class VehicleType(Enum):
    """Vehicle category used for cost comparisons."""

    ELECTRIC = "electric"
    TRADITIONAL = "traditional"
    HYBRID = "hybrid"


@dataclass
class EVVehicleSpecs:
    """Specification sheet describing an electric vehicle."""

    name: str
    purchase_price: float
    battery_capacity_kwh: float
    epa_range_miles: float
    efficiency_kwh_per_mile: float
    warranty_years: int
    warranty_miles: float
    battery_replacement_cost: float
    annual_registration_fee: float
    annual_insurance_cost: float
    maintenance_cost_per_mile: float


@dataclass
class VehicleFinancing:
    """Financing parameters for a vehicle purchase."""

    loan_amount: float
    down_payment: float
    loan_term_years: int
    annual_interest_rate: float
    monthly_payment: Optional[float] = None


@dataclass
class EnergyParameters:
    """Charging mix and annual usage inputs."""

    electricity_rate_per_kwh: float
    home_charging_efficiency: float
    dc_fast_charging_efficiency: float
    annual_miles_driven: float
    percent_home_charged: float
    percent_dc_charged: float
    percent_level2_charged: float

    def validate(self) -> None:
        mix = self.percent_home_charged + self.percent_dc_charged + self.percent_level2_charged
        if abs(mix - 1.0) > 1e-4:
            raise ValueError(
                "Charging percentages must add up to 1.0 (100%). Got %.4f" % mix
            )
        for efficiency in (
            self.home_charging_efficiency,
            self.dc_fast_charging_efficiency,
        ):
            if not 0 < efficiency <= 1:
                raise ValueError("Charging efficiencies must be between 0 and 1")


@dataclass
class TaxIncentives:
    """Tax incentives and rebates available for the purchase."""

    federal_tax_credit: float
    state_tax_credit: float
    local_rebate: float
    utility_rebate: float
    high_income_phase_out: bool = False


@dataclass
class DepreciationParameters:
    """Parameters describing the depreciation curve for a vehicle."""

    method: DepreciationMethod
    useful_life_years: int
    salvage_value: float = 0.0
    declining_balance_rate: float = 0.2
    market_value_curve: Optional[List[float]] = None

    def __post_init__(self) -> None:
        if self.useful_life_years <= 0:
            raise ValueError("Useful life must be a positive integer")
        if self.method is DepreciationMethod.MARKET_BASED and not self.market_value_curve:
            raise ValueError("Market based depreciation requires a value curve")


class EVAcquisitionCalculator:
    """Calculate acquisition expenses, applying incentives and financing."""

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
        rate = self.financing.annual_interest_rate / 12
        periods = self.financing.loan_term_years * 12
        if rate > 0:
            payment = (
                self.financing.loan_amount
                * (rate * (1 + rate) ** periods)
                / ((1 + rate) ** periods - 1)
            )
        else:
            payment = self.financing.loan_amount / periods
        self.financing.monthly_payment = payment

    def get_total_acquisition_cost(self, incentives: Optional[TaxIncentives] = None) -> Dict[str, float]:
        total_incentives = 0.0
        if incentives:
            total_incentives = (
                incentives.federal_tax_credit
                + incentives.state_tax_credit
                + incentives.local_rebate
                + incentives.utility_rebate
            )
        net_cost = max(self.vehicle.purchase_price - total_incentives, 0.0)
        total_financed = self.financing.monthly_payment * self.financing.loan_term_years * 12
        interest_paid = total_financed - self.financing.loan_amount
        return {
            "purchase_price": self.vehicle.purchase_price,
            "down_payment": self.financing.down_payment,
            "registration_fee_year1": self.vehicle.annual_registration_fee,
            "insurance_year1": self.vehicle.annual_insurance_cost,
            "federal_tax_credit": incentives.federal_tax_credit if incentives else 0.0,
            "state_tax_credit": incentives.state_tax_credit if incentives else 0.0,
            "local_rebate": incentives.local_rebate if incentives else 0.0,
            "utility_rebate": incentives.utility_rebate if incentives else 0.0,
            "total_incentives": total_incentives,
            "net_purchase_cost": net_cost,
            "monthly_payment": self.financing.monthly_payment,
            "total_financed_amount": total_financed,
            "total_interest_paid": max(interest_paid, 0.0),
        }

    def amortization_schedule(self) -> List[Dict[str, float]]:
        rate = self.financing.annual_interest_rate / 12
        periods = self.financing.loan_term_years * 12
        payment = self.financing.monthly_payment
        balance = self.financing.loan_amount
        rows = []
        for month in range(1, periods + 1):
            interest = balance * rate
            principal = payment - interest
            balance = max(balance - principal, 0.0)
            rows.append(
                {
                    "month": month,
                    "payment": payment,
                    "principal": principal,
                    "interest": interest,
                    "balance": balance,
                }
            )
        return rows


class OperatingCostCalculator:
    """Estimate yearly energy and maintenance expenditure."""

    def __init__(self, vehicle: EVVehicleSpecs, energy: EnergyParameters):
        energy.validate()
        self.vehicle = vehicle
        self.energy = energy

    def annual_energy_consumption(self) -> Dict[str, float]:
        miles = self.energy.annual_miles_driven
        home_miles = miles * self.energy.percent_home_charged
        dc_miles = miles * self.energy.percent_dc_charged
        level2_miles = miles * self.energy.percent_level2_charged

        home_kwh = home_miles * self.vehicle.efficiency_kwh_per_mile / self.energy.home_charging_efficiency
        dc_kwh = dc_miles * self.vehicle.efficiency_kwh_per_mile / self.energy.dc_fast_charging_efficiency
        # Level2 assumed to share efficiency with home charging for simplicity.
        level2_kwh = level2_miles * self.vehicle.efficiency_kwh_per_mile / self.energy.home_charging_efficiency

        total_kwh = home_kwh + dc_kwh + level2_kwh
        return {
            "home_kwh": home_kwh,
            "dc_fast_kwh": dc_kwh,
            "level2_kwh": level2_kwh,
            "total_kwh": total_kwh,
        }

    def annual_energy_cost(self) -> float:
        usage = self.annual_energy_consumption()
        cost = usage["total_kwh"] * self.energy.electricity_rate_per_kwh
        logger.debug("Annual energy consumption %s leading to cost %.2f", usage, cost)
        return cost

    def annual_maintenance_cost(self) -> float:
        cost = self.vehicle.maintenance_cost_per_mile * self.energy.annual_miles_driven
        logger.debug("Annual maintenance cost calculated as %.2f", cost)
        return cost

    def annual_operating_cost(self) -> float:
        return (
            self.annual_energy_cost()
            + self.annual_maintenance_cost()
            + self.vehicle.annual_registration_fee
            + self.vehicle.annual_insurance_cost
        )

    def lifetime_operating_cost(self, years: int) -> Dict[str, float]:
        energy_cost = self.annual_energy_cost() * years
        maintenance_cost = self.annual_maintenance_cost() * years
        insurance_cost = self.vehicle.annual_insurance_cost * years
        registration_cost = self.vehicle.annual_registration_fee * years
        return {
            "energy_cost": energy_cost,
            "maintenance_cost": maintenance_cost,
            "insurance_cost": insurance_cost,
            "registration_cost": registration_cost,
            "total_operating_cost": energy_cost
            + maintenance_cost
            + insurance_cost
            + registration_cost,
        }


class DepreciationCalculator:
    """Produce depreciation schedules under different methodologies."""

    def __init__(self, purchase_price: float, params: DepreciationParameters):
        self.purchase_price = purchase_price
        self.params = params

    def schedule(self) -> List[Dict[str, float]]:
        method = self.params.method
        if method is DepreciationMethod.STRAIGHT_LINE:
            rows = self._straight_line_schedule()
        elif method is DepreciationMethod.DECLINING_BALANCE:
            rows = self._declining_balance_schedule()
        else:
            rows = self._market_based_schedule()
        return rows

    def _straight_line_schedule(self) -> List[Dict[str, float]]:
        annual = (self.purchase_price - self.params.salvage_value) / self.params.useful_life_years
        book_value = self.purchase_price
        rows = []
        for year in range(1, self.params.useful_life_years + 1):
            book_value = max(book_value - annual, self.params.salvage_value)
            rows.append({"year": year, "depreciation": annual, "book_value": book_value})
        return rows

    def _declining_balance_schedule(self) -> List[Dict[str, float]]:
        rate = self.params.declining_balance_rate
        if not 0 < rate < 1:
            raise ValueError("Declining balance rate must be between 0 and 1")
        book_value = self.purchase_price
        rows = []
        for year in range(1, self.params.useful_life_years + 1):
            depreciation = (book_value - self.params.salvage_value) * rate
            book_value = max(book_value - depreciation, self.params.salvage_value)
            rows.append({"year": year, "depreciation": depreciation, "book_value": book_value})
        return rows

    def _market_based_schedule(self) -> List[Dict[str, float]]:
        curve = self.params.market_value_curve or []
        rows = []
        previous_value = self.purchase_price
        for year, residual in enumerate(curve, start=1):
            residual_value = residual * self.purchase_price
            residual_value = max(residual_value, self.params.salvage_value)
            depreciation = previous_value - residual_value
            rows.append({"year": year, "depreciation": depreciation, "book_value": residual_value})
            previous_value = residual_value
        # Extend schedule with flat salvage if analysis horizon exceeds provided curve.
        if len(rows) < self.params.useful_life_years:
            for year in range(len(rows) + 1, self.params.useful_life_years + 1):
                rows.append(
                    {
                        "year": year,
                        "depreciation": 0.0,
                        "book_value": rows[-1]["book_value"] if rows else self.purchase_price,
                    }
                )
        return rows


class TotalCostOfOwnershipCalculator:
    """Aggregate total cost of ownership (TCO) over an analysis horizon."""

    def __init__(
        self,
        vehicle: EVVehicleSpecs,
        energy: EnergyParameters,
        acquisition: EVAcquisitionCalculator,
        depreciation: DepreciationCalculator,
        incentives: Optional[TaxIncentives] = None,
        analysis_years: int = 8,
    ):
        self.vehicle = vehicle
        self.energy = energy
        self.acquisition = acquisition
        self.depreciation = depreciation
        self.incentives = incentives
        self.analysis_years = analysis_years
        self.operating = OperatingCostCalculator(vehicle, energy)

    def annual_cash_flows(self) -> List[Dict[str, float]]:
        schedule_rows: List[Dict[str, float]] = []
        for year in range(1, self.analysis_years + 1):
            cash_flow = {
                "year": year,
                "loan_payments": (
                    self.acquisition.financing.monthly_payment * 12
                    if year <= self.acquisition.financing.loan_term_years
                    else 0.0
                ),
                "insurance": self.vehicle.annual_insurance_cost,
                "registration": self.vehicle.annual_registration_fee,
                "energy": self.operating.annual_energy_cost(),
                "maintenance": self.operating.annual_maintenance_cost(),
            }
            cash_flow["total"] = sum(
                value for key, value in cash_flow.items() if key != "year"
            )
            schedule_rows.append(cash_flow)
        return schedule_rows

    def summary(self) -> Dict[str, float]:
        acquisition_details = self.acquisition.get_total_acquisition_cost(self.incentives)
        lifetime_operating = self.operating.lifetime_operating_cost(self.analysis_years)
        depreciation_schedule = self.depreciation.schedule()
        relevant_index = min(self.analysis_years, len(depreciation_schedule)) - 1
        end_value = depreciation_schedule[relevant_index]["book_value"]
        total_cash_flow = sum(row["total"] for row in self.annual_cash_flows())
        tco = acquisition_details["net_purchase_cost"] + total_cash_flow - end_value
        return {
            "analysis_years": self.analysis_years,
            "net_purchase_cost": acquisition_details["net_purchase_cost"],
            "total_operating_cost": lifetime_operating["total_operating_cost"],
            "total_energy_cost": lifetime_operating["energy_cost"],
            "total_maintenance_cost": lifetime_operating["maintenance_cost"],
            "total_registration_cost": lifetime_operating["registration_cost"],
            "total_insurance_cost": lifetime_operating["insurance_cost"],
            "total_interest_paid": acquisition_details["total_interest_paid"],
            "residual_value": end_value,
            "total_cost_of_ownership": tco,
        }


class VehicleComparison:
    """Compare TCO across multiple vehicle options."""

    def __init__(self, calculators: Dict[str, TotalCostOfOwnershipCalculator]):
        if not calculators:
            raise ValueError("At least one calculator is required for comparison")
        self.calculators = calculators

    def comparison_table(self) -> List[Dict[str, float]]:
        rows = []
        for name, calculator in self.calculators.items():
            summary = calculator.summary()
            row = {"vehicle": name, **summary}
            rows.append(row)
        return rows

