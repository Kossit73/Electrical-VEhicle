import pytest

from ev_model.finance import (
    DepreciationCalculator,
    DepreciationMethod,
    DepreciationParameters,
    EVAcquisitionCalculator,
    EVComparisonAnalyzer,
    EVEnergyCostsCalculator,
    EVOperatingCostsCalculator,
    EVSensitivityAnalyzer,
    EVTotalCostOfOwnershipAnalyzer,
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

    assert energy_cost == pytest.approx(714.8077, rel=1e-4)
    assert maintenance_cost == pytest.approx(675.0)

    schedule = operating.detailed_operating_costs(years=5)
    assert list(schedule.columns) == [
        "year",
        "annual_miles",
        "cumulative_miles",
        "maintenance_cost",
        "battery_cost",
        "registration_fee",
        "insurance_cost",
        "tire_replacement",
        "total_operating_cost",
    ]
    assert schedule.iloc[0]["total_operating_cost"] == pytest.approx(2155.0)
    assert schedule.loc[schedule["year"] == 4, "tire_replacement"].iloc[0] == pytest.approx(600.0)
    assert schedule.loc[schedule["year"] == 5, "tire_replacement"].iloc[0] == pytest.approx(0.0)

    lifetime = operating.lifetime_operating_cost(5)
    assert lifetime["maintenance_cost"] == pytest.approx(schedule["maintenance_cost"].sum())
    assert lifetime["battery_cost"] == pytest.approx(schedule["battery_cost"].sum())
    assert lifetime["tire_cost"] == pytest.approx(schedule["tire_replacement"].sum())
    assert lifetime["total_operating_cost"] == pytest.approx(
        lifetime["energy_cost"] + schedule["total_operating_cost"].sum()
    )


def test_ev_operating_costs_calculator_handles_warranty(sample_vehicle: EVVehicleSpecs) -> None:
    calc = EVOperatingCostsCalculator(sample_vehicle)
    df = calc.calculate_annual_operating_costs(annual_miles=15000, years=9)

    assert df.loc[df["year"] == 7, "battery_cost"].iloc[0] == pytest.approx(0.0)
    assert df.loc[df["year"] == 8, "battery_cost"].iloc[0] == pytest.approx(0.0)
    assert df.loc[df["year"] == 9, "battery_cost"].iloc[0] == pytest.approx(600.0)
    assert df.loc[df["year"] == 4, "tire_replacement"].iloc[0] == pytest.approx(600.0)


def test_energy_cost_schedule_breakdown(sample_vehicle: EVVehicleSpecs, sample_energy: EnergyParameters) -> None:
    calculator = EVEnergyCostsCalculator(sample_vehicle, sample_energy)
    schedule = calculator.calculate_annual_energy_cost(years=3)

    assert list(schedule.columns) == [
        "year",
        "annual_miles",
        "total_kwh",
        "home_kwh",
        "dc_kwh",
        "level2_kwh",
        "home_charging_cost",
        "dc_charging_cost",
        "level2_charging_cost",
        "total_energy_cost",
        "cost_per_mile",
    ]
    assert schedule.iloc[0]["dc_charging_cost"] == pytest.approx(210.8077, rel=1e-4)
    assert schedule.iloc[1]["total_energy_cost"] == pytest.approx(schedule.iloc[0]["total_energy_cost"])


def test_depreciation_schedules() -> None:
    params = DepreciationParameters(
        method=DepreciationMethod.STRAIGHT_LINE,
        useful_life_years=5,
        salvage_value=6000,
    )
    schedule = DepreciationCalculator(40000, params).schedule()
    assert [row["depreciation"] for row in schedule] == pytest.approx([6800.0] * 5)
    assert schedule[-1]["book_value"] == pytest.approx(6000.0)

    df = DepreciationCalculator(40000, params).dataframe()
    assert "residual_value_percent" in df.columns
    assert df.iloc[-1]["book_value"] == pytest.approx(6000.0)

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
    assert "total_battery_cost" in summary
    assert "total_tire_cost" in summary

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


def test_ev_total_cost_of_ownership_analyzer(
    sample_vehicle: EVVehicleSpecs, sample_energy: EnergyParameters
) -> None:
    analyzer = EVTotalCostOfOwnershipAnalyzer(
        sample_vehicle,
        energy_params=sample_energy,
    )
    results = analyzer.calculate_comprehensive_tco(years=5)

    assert "summary" in results
    assert len(results["annual_details"]) == 5
    summary = results["summary"]
    assert summary["vehicle_name"] == sample_vehicle.name
    assert summary["total_ownership_cost"] > 0
    assert summary["cost_per_mile"] > 0


def test_ev_comparison_analyzer(sample_vehicle: EVVehicleSpecs) -> None:
    analyzer = EVComparisonAnalyzer()
    traditional = {
        "name": "ICE Sedan",
        "initial_cost": 38000.0,
        "mpg": 28.0,
        "fuel_price": 3.8,
        "maintenance_per_mile": 0.09,
        "insurance_per_year": 1400.0,
        "registration_per_year": 220.0,
        "residual_percent": 0.32,
    }

    comparison = analyzer.compare_vehicles(
        sample_vehicle,
        traditional=traditional,
        years=5,
        annual_miles=12_000,
    )

    assert comparison["ev"]["vehicle_name"] == sample_vehicle.name
    assert comparison["traditional"]["total_cost"] > 0
    assert comparison["ev_vs_traditional"]["total_savings"] != 0
    assert comparison["vehicles_compared"]["EV"] == sample_vehicle.name
    assert comparison["vehicles_compared"]["Traditional"] == traditional["name"]


def test_ev_sensitivity_analyzer(sample_vehicle: EVVehicleSpecs, sample_energy: EnergyParameters) -> None:
    base_analyzer = EVTotalCostOfOwnershipAnalyzer(
        vehicle=sample_vehicle,
        energy_params=sample_energy,
    )
    sensitivity = EVSensitivityAnalyzer(base_analyzer)

    results = sensitivity.sensitivity_analysis("electricity_rate", variation_percent=20, years=4)

    assert results["variable"] == "electricity_rate"
    assert len(results["scenarios"]) == 5
    base_value = sample_energy.electricity_rate_per_kwh
    assert results["base_value"] == pytest.approx(base_value)

    for scenario in results["scenarios"]:
        assert "cost_per_mile" in scenario
        assert "impact_percent" in scenario

    # Ensure the base analyzer remains unchanged after sensitivity runs
    assert sample_vehicle.purchase_price == pytest.approx(base_analyzer.vehicle.purchase_price)
    assert sample_energy.electricity_rate_per_kwh == pytest.approx(
        base_analyzer.energy_params.electricity_rate_per_kwh
    )

