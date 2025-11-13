import pytest

from ev_model.finance import (
    DepreciationCalculator,
    DepreciationMethod,
    DepreciationParameters,
    EVAcquisitionCalculator,
    EVVehicleSpecs,
    EnergyParameters,
    OperatingCostCalculator,
    TaxIncentives,
    TotalCostOfOwnershipCalculator,
    VehicleFinancing,
    VehicleComparison,
)


@pytest.fixture
def sample_vehicle() -> EVVehicleSpecs:
    return EVVehicleSpecs(
        name="Econ EV",
        purchase_price=42000,
        battery_capacity_kwh=77,
        epa_range_miles=310,
        efficiency_kwh_per_mile=0.27,
        warranty_years=8,
        warranty_miles=100_000,
        battery_replacement_cost=12000,
        annual_registration_fee=180,
        annual_insurance_cost=1300,
        maintenance_cost_per_mile=0.045,
    )


@pytest.fixture
def sample_energy() -> EnergyParameters:
    return EnergyParameters(
        electricity_rate_per_kwh=0.14,
        home_charging_efficiency=0.9,
        dc_fast_charging_efficiency=0.78,
        annual_miles_driven=15000,
        percent_home_charged=0.6,
        percent_dc_charged=0.2,
        percent_level2_charged=0.2,
    )


def test_acquisition_calculator_handles_incentives(sample_vehicle: EVVehicleSpecs) -> None:
    financing = VehicleFinancing(
        loan_amount=32000,
        down_payment=10000,
        loan_term_years=6,
        annual_interest_rate=0.049,
    )
    calculator = EVAcquisitionCalculator(sample_vehicle, financing)
    incentives = TaxIncentives(7500, 2500, 1000, 500)
    breakdown = calculator.get_total_acquisition_cost(incentives)

    assert pytest.approx(breakdown["monthly_payment"], rel=1e-3) == 513.87
    assert breakdown["net_purchase_cost"] == pytest.approx(30500)
    assert breakdown["total_interest_paid"] == pytest.approx(4998.99, rel=1e-4)


def test_operating_cost_calculator(sample_vehicle: EVVehicleSpecs, sample_energy: EnergyParameters) -> None:
    operating = OperatingCostCalculator(sample_vehicle, sample_energy)
    energy_cost = operating.annual_energy_cost()
    maintenance_cost = operating.annual_maintenance_cost()

    assert energy_cost == pytest.approx(649.38, rel=1e-3)
    assert maintenance_cost == pytest.approx(675.0)


def test_depreciation_schedules() -> None:
    params = DepreciationParameters(
        method=DepreciationMethod.STRAIGHT_LINE,
        useful_life_years=5,
        salvage_value=6000,
    )
    schedule = DepreciationCalculator(40000, params).schedule()
    assert [row["depreciation"] for row in schedule] == pytest.approx([6800.0] * 5)
    assert schedule[-1]["book_value"] == pytest.approx(6000.0)

    declining = DepreciationParameters(
        method=DepreciationMethod.DECLINING_BALANCE,
        useful_life_years=5,
        salvage_value=4000,
        declining_balance_rate=0.25,
    )
    declining_schedule = DepreciationCalculator(40000, declining).schedule()
    assert len(declining_schedule) == 5
    assert declining_schedule[-1]["book_value"] >= 4000


def test_total_cost_of_ownership_summary(sample_vehicle: EVVehicleSpecs, sample_energy: EnergyParameters) -> None:
    financing = VehicleFinancing(
        loan_amount=33600,
        down_payment=8400,
        loan_term_years=5,
        annual_interest_rate=0.045,
    )
    acquisition = EVAcquisitionCalculator(sample_vehicle, financing)
    depreciation_params = DepreciationParameters(
        method=DepreciationMethod.STRAIGHT_LINE,
        useful_life_years=8,
        salvage_value=12000,
    )
    depreciation = DepreciationCalculator(sample_vehicle.purchase_price, depreciation_params)
    incentives = TaxIncentives(7500, 2000, 500, 250)
    calculator = TotalCostOfOwnershipCalculator(
        sample_vehicle,
        sample_energy,
        acquisition,
        depreciation,
        incentives,
        analysis_years=8,
    )

    summary = calculator.summary()
    assert summary["analysis_years"] == 8
    assert summary["residual_value"] == pytest.approx(12000.0)
    assert summary["total_cost_of_ownership"] > 0

    cash_flows = calculator.annual_cash_flows()
    assert len(cash_flows) == 8
    assert cash_flows[-1]["loan_payments"] == 0


def test_vehicle_comparison(sample_vehicle: EVVehicleSpecs, sample_energy: EnergyParameters) -> None:
    financing = VehicleFinancing(
        loan_amount=33000,
        down_payment=9000,
        loan_term_years=5,
        annual_interest_rate=0.04,
    )
    acquisition = EVAcquisitionCalculator(sample_vehicle, financing)
    depreciation_params = DepreciationParameters(
        method=DepreciationMethod.STRAIGHT_LINE,
        useful_life_years=8,
        salvage_value=10000,
    )
    depreciation = DepreciationCalculator(sample_vehicle.purchase_price, depreciation_params)
    tco = TotalCostOfOwnershipCalculator(
        sample_vehicle,
        sample_energy,
        acquisition,
        depreciation,
        analysis_years=6,
    )

    comparison = VehicleComparison({sample_vehicle.name: tco})
    table = comparison.comparison_table()
    assert len(table) == 1
    assert table[0]["vehicle"] == sample_vehicle.name
    assert table[0]["analysis_years"] == 6

