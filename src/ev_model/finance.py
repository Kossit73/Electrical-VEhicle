"""Comprehensive tools for analysing EV ownership costs."""

from __future__ import annotations

import logging
from dataclasses import dataclass, replace
from enum import Enum
from typing import Any, Dict, List, Optional

try:  # pragma: no cover - exercised indirectly through unit tests
    import pandas as pd
except ModuleNotFoundError:  # pragma: no cover - minimal fallback when pandas unavailable
    class _MiniSeries(list):
        def sum(self) -> float:
            return float(sum(self))

        def __eq__(self, other: object) -> List[bool]:  # type: ignore[override]
            return [value == other for value in self]

        @property
        def iloc(self) -> "_MiniSeriesIndexer":
            return _MiniSeriesIndexer(self)

    class _MiniSeriesIndexer:
        def __init__(self, data: _MiniSeries):
            self._data = data

        def __getitem__(self, index):
            return self._data[index]

    class _MiniRow(dict):
        pass

    class _MiniILocRows:
        def __init__(self, rows: List[_MiniRow]):
            self._rows = rows

        def __getitem__(self, index):
            if isinstance(index, slice):
                return self._rows[index]
            return self._rows[index]

    class _MiniLocIndexer:
        def __init__(self, df: "_MiniDataFrame"):
            self._df = df

        def __getitem__(self, key):
            mask, column = key
            if isinstance(mask, _MiniSeries):
                mask_iter = list(mask)
            else:
                mask_iter = list(mask)
            filtered_rows = [row for row, keep in zip(self._df._rows, mask_iter) if keep]
            return _MiniSeries([row[column] for row in filtered_rows])

    class _MiniDataFrame:
        def __init__(self, rows: List[Dict[str, float]]):
            self._rows: List[_MiniRow] = [
                _MiniRow(row) for row in rows
            ]
            self._columns = list(rows[0].keys()) if rows else []

        @property
        def columns(self) -> List[str]:
            return self._columns

        def __getitem__(self, column: str) -> _MiniSeries:
            return _MiniSeries([row[column] for row in self._rows])

        @property
        def iloc(self) -> _MiniILocRows:
            return _MiniILocRows(self._rows)

        @property
        def loc(self) -> _MiniLocIndexer:
            return _MiniLocIndexer(self)

        def __len__(self) -> int:
            return len(self._rows)

        def to_dict(self, orient: str = "records") -> List[Dict[str, float]]:
            if orient != "records":  # pragma: no cover - unused orientation in fallback
                raise NotImplementedError("_MiniDataFrame only supports records orientation")
            return [dict(row) for row in self._rows]

    class _MiniPandasModule:
        DataFrame = _MiniDataFrame

    pd = _MiniPandasModule()


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
    declining_balance_rate: Optional[float] = None
    annual_miles: float = 12000.0
    market_value_curve: Optional[List[float]] = None

    def __post_init__(self) -> None:
        if self.useful_life_years <= 0:
            raise ValueError("Useful life must be a positive integer")
        if self.annual_miles < 0:
            raise ValueError("Annual miles cannot be negative")


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


class EVOperatingCostsCalculator:
    """Calculate operating costs for electric vehicles with detailed projections."""

    _TIRE_LIFE_MILES = 50_000
    _TIRE_COST_PER_TIRE = 150.0

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
        """Calculate year-by-year operating costs with inflation and wear factors."""

        if years <= 0:
            raise ValueError("Years must be positive for operating cost projections")

        results: List[Dict[str, float]] = []
        registration_fee = (
            annual_registration if annual_registration is not None else self.vehicle.annual_registration_fee
        )
        insurance_cost = (
            annual_insurance if annual_insurance is not None else self.vehicle.annual_insurance_cost
        )

        for year in range(1, years + 1):
            cumulative_miles = annual_miles * year

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
                    "cumulative_miles": cumulative_miles,
                    "maintenance_cost": maintenance_cost,
                    "battery_cost": battery_degradation_cost,
                    "registration_fee": registration,
                    "insurance_cost": insurance,
                    "tire_replacement": tire_cost,
                    "total_operating_cost": total_operating,
                }
            )

        return pd.DataFrame(results)

    # ------------------------------------------------------------------
    # Internal helpers
    def _calculate_battery_costs(self, year: int, annual_miles: float) -> float:
        """Estimate battery reserves once warranty coverage lapses."""

        if self.vehicle.battery_replacement_cost <= 0:
            return 0.0

        if year <= self.vehicle.warranty_years:
            return 0.0

        years_past_warranty = year - self.vehicle.warranty_years
        reserve_rate = 0.05  # 5% annual reserve for potential post-warranty replacement
        battery_cost = self.vehicle.battery_replacement_cost * reserve_rate * years_past_warranty
        return max(0.0, battery_cost)

    def _calculate_tire_replacement_cost(self, year: int, annual_miles: float) -> float:
        """Estimate tyre replacement costs based on cumulative mileage."""

        cumulative_miles = annual_miles * year
        previous_miles = annual_miles * (year - 1)
        tire_replacement_cost = self._TIRE_COST_PER_TIRE * 4

        if self._TIRE_LIFE_MILES <= 0:
            return 0.0

        replacements = int(cumulative_miles / self._TIRE_LIFE_MILES)
        previous_replacements = int(previous_miles / self._TIRE_LIFE_MILES)
        replacements_this_year = max(0, replacements - previous_replacements)
        return replacements_this_year * tire_replacement_cost


class EVEnergyCostsCalculator:
    """Calculate annual EV energy usage and charging costs."""

    def __init__(self, vehicle: EVVehicleSpecs, energy_params: EnergyParameters):
        energy_params.validate()
        self.vehicle = vehicle
        self.energy_params = energy_params

    def calculate_annual_energy_cost(self, years: int = 10) -> pd.DataFrame:
        """Return a schedule of annual energy usage by charging method."""

        if years <= 0:
            raise ValueError("Years must be positive for energy cost projections")

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
            cost_per_mile = total_energy_cost / annual_miles if annual_miles > 0 else 0.0

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


class OperatingCostCalculator:
    """Estimate yearly energy and maintenance expenditure."""

    def __init__(
        self,
        vehicle: EVVehicleSpecs,
        energy: EnergyParameters,
        maintenance_inflation_rate: float = 0.02,
    ):
        self.vehicle = vehicle
        self.energy = energy
        self.maintenance_inflation_rate = maintenance_inflation_rate
        self.energy_costs = EVEnergyCostsCalculator(vehicle, energy)

    def annual_energy_consumption(self) -> Dict[str, float]:
        schedule = self.energy_costs.calculate_annual_energy_cost(years=1)
        row = schedule.iloc[0] if len(schedule) else {}
        return {
            "home_kwh": float(row.get("home_kwh", 0.0)),
            "dc_fast_kwh": float(row.get("dc_kwh", 0.0)),
            "level2_kwh": float(row.get("level2_kwh", 0.0)),
            "total_kwh": float(row.get("total_kwh", 0.0)),
        }

    def annual_energy_cost(self) -> float:
        schedule = self.energy_costs.calculate_annual_energy_cost(years=1)
        total_cost = float(schedule.iloc[0]["total_energy_cost"]) if len(schedule) else 0.0
        logger.debug("Annual energy cost schedule %s", schedule.iloc[0] if len(schedule) else {})
        return total_cost

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

    def detailed_operating_costs(self, years: int) -> pd.DataFrame:
        """Return a detailed operating cost schedule for the analysis horizon."""

        calculator = EVOperatingCostsCalculator(self.vehicle)
        return calculator.calculate_annual_operating_costs(
            annual_miles=self.energy.annual_miles_driven,
            annual_registration=self.vehicle.annual_registration_fee,
            annual_insurance=self.vehicle.annual_insurance_cost,
            maintenance_inflation_rate=self.maintenance_inflation_rate,
            years=years,
        )

    def energy_cost_schedule(self, years: int) -> pd.DataFrame:
        """Return a detailed energy cost schedule for the requested horizon."""

        return self.energy_costs.calculate_annual_energy_cost(years)

    def lifetime_operating_cost(self, years: int) -> Dict[str, float]:
        schedule = self.detailed_operating_costs(years)
        energy_schedule = self.energy_costs.calculate_annual_energy_cost(years)
        energy_cost = float(energy_schedule["total_energy_cost"].sum())
        maintenance_cost = float(schedule["maintenance_cost"].sum())
        insurance_cost = float(schedule["insurance_cost"].sum())
        registration_cost = float(schedule["registration_fee"].sum())
        battery_cost = float(schedule["battery_cost"].sum())
        tire_cost = float(schedule["tire_replacement"].sum())
        other_operating = float(schedule["total_operating_cost"].sum())
        return {
            "energy_cost": energy_cost,
            "maintenance_cost": maintenance_cost,
            "insurance_cost": insurance_cost,
            "registration_cost": registration_cost,
            "battery_cost": battery_cost,
            "tire_cost": tire_cost,
            "total_operating_cost": energy_cost + other_operating,
        }


class DepreciationCalculator:
    """Produce depreciation schedules under different methodologies."""

    def __init__(
        self,
        purchase_price: float,
        params: DepreciationParameters,
        vehicle_type: VehicleType = VehicleType.ELECTRIC,
    ):
        self.purchase_price = purchase_price
        self.params = params
        self.vehicle_type = vehicle_type

    def calculate_depreciation(
        self,
        initial_value: float,
        years: int = 10,
        method: DepreciationMethod = DepreciationMethod.MARKET_BASED,
        annual_miles: float = 12000,
        salvage_value: float = 0.0,
        declining_balance_rate: Optional[float] = None,
        market_value_curve: Optional[List[float]] = None,
    ) -> pd.DataFrame:
        """Calculate depreciation using the specified method."""

        if years <= 0:
            raise ValueError("Years must be a positive integer")

        if method is DepreciationMethod.STRAIGHT_LINE:
            rows = self._straight_line_depreciation(initial_value, years, salvage_value)
        elif method is DepreciationMethod.DECLINING_BALANCE:
            rows = self._declining_balance_depreciation(
                initial_value,
                years,
                salvage_value,
                declining_balance_rate,
            )
        else:
            rows = self._market_based_depreciation(
                initial_value,
                years,
                annual_miles,
                salvage_value,
                market_value_curve,
            )

        return pd.DataFrame(rows)

    def schedule(self) -> List[Dict[str, float]]:
        """Backwards compatible schedule representation used across the package."""

        dataframe = self.calculate_depreciation(
            initial_value=self.purchase_price,
            years=self.params.useful_life_years,
            method=self.params.method,
            annual_miles=self.params.annual_miles,
            salvage_value=self.params.salvage_value,
            declining_balance_rate=self.params.declining_balance_rate,
            market_value_curve=self.params.market_value_curve,
        )

        return [
            {
                "year": int(row["year"]),
                "depreciation": float(row["depreciation_amount"]),
                "book_value": float(row["book_value"]),
                "cumulative_depreciation": float(row["cumulative_depreciation"]),
            }
            for row in dataframe.to_dict("records")
        ]

    def dataframe(self) -> pd.DataFrame:
        """Return the depreciation schedule as a DataFrame for further analysis."""

        return self.calculate_depreciation(
            initial_value=self.purchase_price,
            years=self.params.useful_life_years,
            method=self.params.method,
            annual_miles=self.params.annual_miles,
            salvage_value=self.params.salvage_value,
            declining_balance_rate=self.params.declining_balance_rate,
            market_value_curve=self.params.market_value_curve,
        )

    def _straight_line_depreciation(
        self,
        initial_value: float,
        years: int,
        salvage_value: float,
    ) -> List[Dict[str, float]]:
        """Straight-line depreciation: equal annual reduction."""

        salvage_value = min(salvage_value, initial_value)
        base_value = max(initial_value - salvage_value, 0.0)
        annual_depreciation = base_value / years
        results: List[Dict[str, float]] = []

        for year in range(1, years + 1):
            book_value = max(salvage_value, initial_value - annual_depreciation * year)
            cumulative = initial_value - book_value
            results.append(
                {
                    "year": year,
                    "depreciation_amount": annual_depreciation,
                    "cumulative_depreciation": cumulative,
                    "book_value": book_value,
                    "residual_value_percent": (book_value / initial_value) * 100,
                }
            )

        return results

    def _declining_balance_depreciation(
        self,
        initial_value: float,
        years: int,
        salvage_value: float,
        rate_override: Optional[float],
    ) -> List[Dict[str, float]]:
        """Double declining balance depreciation: faster initial depreciation."""

        salvage_value = min(salvage_value, initial_value)
        rate = rate_override if rate_override is not None else 2 / (years + 1)
        if not 0 < rate < 1:
            raise ValueError("Declining balance rate must be between 0 and 1")

        results: List[Dict[str, float]] = []
        book_value = initial_value
        cumulative = 0.0

        for year in range(1, years + 1):
            annual_depreciation = book_value * rate
            next_book_value = book_value - annual_depreciation
            if next_book_value < salvage_value:
                annual_depreciation = book_value - salvage_value
                next_book_value = salvage_value

            cumulative += annual_depreciation
            book_value = next_book_value

            results.append(
                {
                    "year": year,
                    "depreciation_amount": annual_depreciation,
                    "cumulative_depreciation": cumulative,
                    "book_value": book_value,
                    "residual_value_percent": max(0.0, (book_value / initial_value) * 100),
                }
            )

        return results

    def _market_based_depreciation(
        self,
        initial_value: float,
        years: int,
        annual_miles: float,
        salvage_value: float,
        market_value_curve: Optional[List[float]],
    ) -> List[Dict[str, float]]:
        """Market-based depreciation using empirical EV depreciation curves."""

        salvage_value = min(salvage_value, initial_value)
        if market_value_curve:
            return self._curve_based_depreciation(
                initial_value,
                years,
                salvage_value,
                market_value_curve,
            )

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

        results: List[Dict[str, float]] = []
        book_value = initial_value
        cumulative = 0.0

        for year in range(1, years + 1):
            rate = depreciation_schedule.get(year, 0.03)
            annual_depreciation = book_value * rate
            next_book_value = book_value - annual_depreciation

            cumulative_miles = annual_miles * year
            if cumulative_miles > 150000:
                mileage_factor = (cumulative_miles - 150000) / 1_000_000
                additional_rate = min(0.10, mileage_factor * 0.05)
                additional_depreciation = book_value * additional_rate
                next_book_value -= additional_depreciation
                annual_depreciation += additional_depreciation

            if next_book_value < salvage_value:
                annual_depreciation = book_value - salvage_value
                next_book_value = salvage_value

            cumulative += annual_depreciation
            book_value = next_book_value

            results.append(
                {
                    "year": year,
                    "depreciation_amount": annual_depreciation,
                    "cumulative_depreciation": cumulative,
                    "book_value": book_value,
                    "residual_value_percent": max(0.0, (book_value / initial_value) * 100),
                }
            )

        return results

    def _curve_based_depreciation(
        self,
        initial_value: float,
        years: int,
        salvage_value: float,
        market_value_curve: List[float],
    ) -> List[Dict[str, float]]:
        """Legacy market-curve support using residual value percentages."""

        salvage_value = min(salvage_value, initial_value)
        results: List[Dict[str, float]] = []
        previous_value = initial_value
        cumulative = 0.0

        for year, residual in enumerate(market_value_curve, start=1):
            residual_value = max(residual * initial_value, salvage_value)
            depreciation = previous_value - residual_value
            cumulative += depreciation
            results.append(
                {
                    "year": year,
                    "depreciation_amount": depreciation,
                    "cumulative_depreciation": cumulative,
                    "book_value": residual_value,
                    "residual_value_percent": max(0.0, (residual_value / initial_value) * 100),
                }
            )
            previous_value = residual_value

        # Extend out to requested horizon if the curve is shorter.
        if len(results) < years:
            book_value = results[-1]["book_value"] if results else initial_value
            for year in range(len(results) + 1, years + 1):
                results.append(
                    {
                        "year": year,
                        "depreciation_amount": 0.0,
                        "cumulative_depreciation": cumulative,
                        "book_value": book_value,
                        "residual_value_percent": max(0.0, (book_value / initial_value) * 100),
                    }
                )

        return results


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
            "total_battery_cost": lifetime_operating["battery_cost"],
            "total_tire_cost": lifetime_operating["tire_cost"],
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


class EVTotalCostOfOwnershipAnalyzer:
    """Perform a comprehensive TCO analysis for a single EV configuration."""

    def __init__(
        self,
        vehicle: EVVehicleSpecs,
        financing: Optional[VehicleFinancing] = None,
        energy_params: Optional[EnergyParameters] = None,
        incentives: Optional[TaxIncentives] = None,
        depreciation_params: Optional[DepreciationParameters] = None,
    ) -> None:
        self.vehicle = vehicle
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
        self.depreciation_params = depreciation_params or DepreciationParameters(
            method=DepreciationMethod.MARKET_BASED,
            useful_life_years=max(self.vehicle.warranty_years, 10),
            annual_miles=self.energy_params.annual_miles_driven,
        )
        self.depreciation_calc = DepreciationCalculator(
            vehicle.purchase_price, self.depreciation_params
        )

        # Normalise financing reference so downstream consumers always have details
        self.financing = self.acquisition_calc.financing

    def _to_records(self, frame: pd.DataFrame) -> List[Dict[str, float]]:
        """Convert a DataFrame-like object into a list of dictionaries."""

        if hasattr(frame, "to_dict"):
            return frame.to_dict("records")  # type: ignore[arg-type]
        raise TypeError("Unsupported frame type for record conversion")

    def calculate_comprehensive_tco(self, years: int = 10) -> Dict[str, Any]:
        """Calculate detailed total cost of ownership information."""

        if years <= 0:
            raise ValueError("Years must be a positive integer for TCO analysis")

        acquisition = self.acquisition_calc.get_total_acquisition_cost(self.incentives)
        operating_df = self.operating_calc.calculate_annual_operating_costs(
            annual_miles=self.energy_params.annual_miles_driven, years=years
        )
        energy_df = self.energy_calc.calculate_annual_energy_cost(years=years)
        depreciation_df = self.depreciation_calc.calculate_depreciation(
            initial_value=acquisition["net_purchase_cost"],
            years=years,
            method=self.depreciation_params.method,
            annual_miles=self.depreciation_params.annual_miles,
            salvage_value=self.depreciation_params.salvage_value,
            declining_balance_rate=self.depreciation_params.declining_balance_rate,
            market_value_curve=self.depreciation_params.market_value_curve,
        )

        operating_records = self._to_records(operating_df)
        energy_records = self._to_records(energy_df)
        depreciation_records = self._to_records(depreciation_df)

        financing_payment = self.financing.monthly_payment or 0.0
        financing_years = self.financing.loan_term_years
        annual_miles = self.energy_params.annual_miles_driven

        tco_rows: List[Dict[str, float]] = []
        cumulative_cost = 0.0
        cumulative_financing = 0.0

        for idx in range(years):
            year = idx + 1
            financing_cost = financing_payment * 12 if year <= financing_years else 0.0
            cumulative_financing += financing_cost

            operating_cost = (
                operating_records[idx]["total_operating_cost"]
                if idx < len(operating_records)
                else 0.0
            )
            energy_cost = (
                energy_records[idx]["total_energy_cost"]
                if idx < len(energy_records)
                else 0.0
            )
            total_annual_cost = financing_cost + operating_cost + energy_cost
            cumulative_cost += total_annual_cost

            residual_value = (
                depreciation_records[idx]["book_value"]
                if idx < len(depreciation_records)
                else 0.0
            )
            cumulative_miles = annual_miles * year
            cost_per_mile = cumulative_cost / cumulative_miles if cumulative_miles else 0.0

            tco_rows.append(
                {
                    "year": year,
                    "financing_cost": financing_cost,
                    "operating_cost": operating_cost,
                    "energy_cost": energy_cost,
                    "total_annual_cost": total_annual_cost,
                    "cumulative_cost": cumulative_cost,
                    "cumulative_financing": cumulative_financing,
                    "residual_value": residual_value,
                    "net_cost_after_residual": cumulative_cost - residual_value,
                    "cumulative_miles": cumulative_miles,
                    "cost_per_mile": cost_per_mile,
                }
            )

        total_cost = sum(row["total_annual_cost"] for row in tco_rows)
        total_miles = annual_miles * years
        final_residual = tco_rows[-1]["residual_value"] if tco_rows else 0.0
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
            "cost_per_mile": net_cost / total_miles if total_miles else 0.0,
            "financing_years": financing_years,
            "financing_interest_rate": self.financing.annual_interest_rate,
        }

        return {
            "acquisition": acquisition,
            "annual_details": pd.DataFrame(tco_rows).to_dict("records"),
            "operating_details": operating_records,
            "energy_details": energy_records,
            "depreciation_details": depreciation_records,
            "summary": summary,
        }


class EVComparisonAnalyzer:
    """Compare EV ownership costs against traditional and hybrid alternatives."""

    def __init__(self) -> None:
        pass

    def compare_vehicles(
        self,
        ev: EVVehicleSpecs,
        traditional: Optional[Dict[str, float]] = None,
        hybrid: Optional[Dict[str, float]] = None,
        years: int = 10,
        annual_miles: float = 12_000,
        energy_params: Optional[EnergyParameters] = None,
    ) -> Dict[str, Any]:
        """Return a cost comparison across EV, traditional, and hybrid vehicles.

        Args:
            ev: Electric vehicle specifications to analyse.
            traditional: Optional ICE vehicle cost assumptions.
            hybrid: Optional hybrid vehicle cost assumptions.
            years: Analysis horizon in years.
            annual_miles: Annual miles used for all scenarios.
            energy_params: Optional charging mix and rate overrides for the EV.
        """

        if energy_params is not None:
            ev_energy_params = replace(
                energy_params, annual_miles_driven=annual_miles
            )
        else:
            ev_energy_params = EnergyParameters(
                electricity_rate_per_kwh=0.14,
                home_charging_efficiency=0.90,
                dc_fast_charging_efficiency=0.80,
                annual_miles_driven=annual_miles,
                percent_home_charged=0.7,
                percent_dc_charged=0.1,
                percent_level2_charged=0.2,
            )

        ev_analyzer = EVTotalCostOfOwnershipAnalyzer(
            vehicle=ev,
            energy_params=ev_energy_params,
        )
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
            traditional_tco = self._calculate_traditional_vehicle_tco(
                traditional, years, annual_miles
            )
            comparison["traditional"] = traditional_tco
            comparison["ev_vs_traditional"] = self._calculate_savings(
                ev_tco["summary"]["net_ownership_cost"],
                traditional_tco["net_cost"],
                ev_tco["summary"]["initial_cost"],
                traditional.get("initial_cost", traditional.get("purchase_price", 0.0)),
                years,
            )

        if hybrid:
            hybrid_tco = self._calculate_hybrid_vehicle_tco(hybrid, years, annual_miles)
            comparison["hybrid"] = hybrid_tco
            comparison["ev_vs_hybrid"] = self._calculate_savings(
                ev_tco["summary"]["net_ownership_cost"],
                hybrid_tco["net_cost"],
                ev_tco["summary"]["initial_cost"],
                hybrid.get("initial_cost", hybrid.get("purchase_price", 0.0)),
                years,
            )

        return comparison

    def _calculate_traditional_vehicle_tco(
        self,
        vehicle: Dict[str, float],
        years: int,
        annual_miles: float,
    ) -> Dict[str, float]:
        """Calculate total cost of ownership for a traditional vehicle."""

        annual_fuel_cost = (annual_miles / vehicle.get("mpg", 25.0)) * vehicle.get(
            "fuel_price", 3.5
        )
        maintenance_cost = annual_miles * vehicle.get("maintenance_per_mile", 0.08)
        annual_insurance = vehicle.get("insurance_per_year", 1200.0)
        annual_registration = vehicle.get("registration_per_year", 200.0)

        annual_cost = (
            annual_fuel_cost
            + maintenance_cost
            + annual_insurance
            + annual_registration
        )

        financing_cost = vehicle.get("monthly_payment", 400.0) * 12 * 6
        total_cost = (annual_cost * years) + financing_cost
        initial_cost = vehicle.get("initial_cost", vehicle.get("purchase_price", 30_000.0))
        residual_value = initial_cost * vehicle.get("residual_percent", 0.4)

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
        """Calculate total cost of ownership for a hybrid vehicle."""

        annual_fuel_cost = (annual_miles / vehicle.get("mpg_combined", 50.0)) * vehicle.get(
            "fuel_price", 3.5
        )
        maintenance_cost = annual_miles * vehicle.get("maintenance_per_mile", 0.05)
        annual_insurance = vehicle.get("insurance_per_year", 1300.0)
        annual_registration = vehicle.get("registration_per_year", 200.0)

        annual_cost = (
            annual_fuel_cost
            + maintenance_cost
            + annual_insurance
            + annual_registration
        )

        financing_cost = vehicle.get("monthly_payment", 500.0) * 12 * 6
        total_cost = (annual_cost * years) + financing_cost
        initial_cost = vehicle.get("initial_cost", vehicle.get("purchase_price", 35_000.0))
        residual_value = initial_cost * vehicle.get("residual_percent", 0.45)

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
        """Calculate cost savings and payback period when switching to an EV."""

        total_savings = alternative_cost - ev_cost
        annual_savings = total_savings / years if years else 0.0
        price_premium = ev_purchase_price - alternative_price

        if annual_savings > 0:
            payback_years = min(years, price_premium / annual_savings) if price_premium > 0 else 0
        else:
            payback_years = None

        return {
            "total_savings": total_savings,
            "annual_savings": annual_savings,
            "price_premium": price_premium,
            "payback_period_years": payback_years,
            "savings_percent": (total_savings / alternative_cost * 100) if alternative_cost else 0.0,
        }


class EVSensitivityAnalyzer:
    """Perform sensitivity analysis on the total cost of ownership model."""

    def __init__(self, base_tco_analysis: EVTotalCostOfOwnershipAnalyzer) -> None:
        self.base_analyzer = base_tco_analysis

    def sensitivity_analysis(
        self,
        variable: str,
        variation_percent: float = 10,
        years: int = 10,
    ) -> Dict[str, Any]:
        """Evaluate the effect of varying a key input on cost-per-mile outcomes."""

        if variation_percent <= 0:
            raise ValueError("variation_percent must be positive for sensitivity analysis")

        base_tco = self.base_analyzer.calculate_comprehensive_tco(years=years)
        base_cost_per_mile = base_tco["summary"]["cost_per_mile"]

        spread = variation_percent / 100.0
        half_spread = spread / 2
        factors = [1 - spread, 1 - half_spread, 1.0, 1 + half_spread, 1 + spread]

        results: Dict[str, Any] = {
            "variable": variable,
            "base_value": self._get_variable_value(variable),
            "base_cost_per_mile": base_cost_per_mile,
            "scenarios": [],
        }

        for factor in factors:
            modified_analyzer = self._create_modified_analyzer(variable, factor)
            modified_tco = modified_analyzer.calculate_comprehensive_tco(years=years)
            new_cost_per_mile = modified_tco["summary"]["cost_per_mile"]
            cost_impact = new_cost_per_mile - base_cost_per_mile

            results["scenarios"].append(
                {
                    "factor": factor,
                    "change_percent": (factor - 1) * 100,
                    "new_value": self._get_variable_value(variable, factor),
                    "cost_per_mile": new_cost_per_mile,
                    "cost_impact": cost_impact,
                    "impact_percent": (cost_impact / base_cost_per_mile * 100)
                    if base_cost_per_mile
                    else 0.0,
                }
            )

        return results

    def _get_variable_value(self, variable: str, factor: float = 1.0) -> float:
        """Return the current or scaled value for a variable under test."""

        if variable == "electricity_rate":
            return self.base_analyzer.energy_params.electricity_rate_per_kwh * factor
        if variable == "annual_miles":
            return self.base_analyzer.energy_params.annual_miles_driven * factor
        if variable == "purchase_price":
            return self.base_analyzer.vehicle.purchase_price * factor
        if variable == "battery_cost":
            return self.base_analyzer.vehicle.battery_replacement_cost * factor
        return 0.0

    def _create_modified_analyzer(
        self,
        variable: str,
        factor: float,
    ) -> EVTotalCostOfOwnershipAnalyzer:
        """Create a cloned analyzer with a single parameter adjusted."""

        energy_params = EnergyParameters(
            electricity_rate_per_kwh=self.base_analyzer.energy_params.electricity_rate_per_kwh,
            home_charging_efficiency=self.base_analyzer.energy_params.home_charging_efficiency,
            dc_fast_charging_efficiency=self.base_analyzer.energy_params.dc_fast_charging_efficiency,
            annual_miles_driven=self.base_analyzer.energy_params.annual_miles_driven,
            percent_home_charged=self.base_analyzer.energy_params.percent_home_charged,
            percent_dc_charged=self.base_analyzer.energy_params.percent_dc_charged,
            percent_level2_charged=self.base_analyzer.energy_params.percent_level2_charged,
        )

        vehicle = replace(self.base_analyzer.vehicle)
        financing = replace(self.base_analyzer.financing) if self.base_analyzer.financing else None

        if variable == "electricity_rate":
            energy_params.electricity_rate_per_kwh *= factor
        elif variable == "annual_miles":
            energy_params.annual_miles_driven *= factor
        elif variable == "purchase_price":
            vehicle = replace(vehicle, purchase_price=vehicle.purchase_price * factor)
        elif variable == "battery_cost":
            vehicle = replace(
                vehicle,
                battery_replacement_cost=vehicle.battery_replacement_cost * factor,
            )

        return EVTotalCostOfOwnershipAnalyzer(
            vehicle=vehicle,
            financing=financing,
            energy_params=energy_params,
            incentives=self.base_analyzer.incentives,
            depreciation_params=self.base_analyzer.depreciation_params,
        )
