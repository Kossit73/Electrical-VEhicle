"""Test data and example usage for the EV Financial Model."""

from __future__ import annotations

import pandas as pd

from ev_model import (
    EVComparisonAnalyzer,
    EVSensitivityAnalyzer,
    EVTotalCostOfOwnershipAnalyzer,
    EVVehicleSpecs,
    EnergyParameters,
    TaxIncentives,
    VehicleFinancing,
)


def create_sample_evs() -> dict[str, EVVehicleSpecs]:
    """Create sample EV vehicle specifications."""

    return {
        "tesla_model_3": EVVehicleSpecs(
            name="Tesla Model 3 (Standard Range Plus)",
            purchase_price=46_995,
            battery_capacity_kwh=54,
            epa_range_miles=263,
            efficiency_kwh_per_mile=0.205,
            warranty_years=8,
            warranty_miles=120_000,
            battery_replacement_cost=7_000,
            annual_registration_fee=250,
            annual_insurance_cost=1_200,
            maintenance_cost_per_mile=0.02,
        ),
        "chevy_bolt": EVVehicleSpecs(
            name="Chevrolet Bolt EV",
            purchase_price=42_000,
            battery_capacity_kwh=65,
            epa_range_miles=260,
            efficiency_kwh_per_mile=0.210,
            warranty_years=8,
            warranty_miles=100_000,
            battery_replacement_cost=6_000,
            annual_registration_fee=180,
            annual_insurance_cost=1_100,
            maintenance_cost_per_mile=0.015,
        ),
        "nissan_leaf": EVVehicleSpecs(
            name="Nissan Leaf (SV Plus)",
            purchase_price=35_850,
            battery_capacity_kwh=62,
            epa_range_miles=226,
            efficiency_kwh_per_mile=0.230,
            warranty_years=8,
            warranty_miles=100_000,
            battery_replacement_cost=5_500,
            annual_registration_fee=200,
            annual_insurance_cost=1_050,
            maintenance_cost_per_mile=0.018,
        ),
    }


def create_sample_financing() -> dict[str, VehicleFinancing]:
    """Create sample financing options."""

    return {
        "standard_loan": VehicleFinancing(
            loan_amount=35_000,
            down_payment=10_000,
            loan_term_years=5,
            annual_interest_rate=0.045,
        ),
        "low_rate_loan": VehicleFinancing(
            loan_amount=32_000,
            down_payment=10_000,
            loan_term_years=5,
            annual_interest_rate=0.025,
        ),
        "lease": VehicleFinancing(
            loan_amount=0,
            down_payment=3_000,
            loan_term_years=3,
            annual_interest_rate=0.0,
        ),
    }


def create_sample_energy_params() -> dict[str, EnergyParameters]:
    """Create sample energy parameters."""

    return {
        "california": EnergyParameters(
            electricity_rate_per_kwh=0.18,
            home_charging_efficiency=0.90,
            dc_fast_charging_efficiency=0.80,
            annual_miles_driven=12_000,
            percent_home_charged=0.70,
            percent_dc_charged=0.10,
            percent_level2_charged=0.20,
        ),
        "texas": EnergyParameters(
            electricity_rate_per_kwh=0.11,
            home_charging_efficiency=0.90,
            dc_fast_charging_efficiency=0.80,
            annual_miles_driven=14_000,
            percent_home_charged=0.80,
            percent_dc_charged=0.05,
            percent_level2_charged=0.15,
        ),
        "new_york": EnergyParameters(
            electricity_rate_per_kwh=0.16,
            home_charging_efficiency=0.90,
            dc_fast_charging_efficiency=0.80,
            annual_miles_driven=10_000,
            percent_home_charged=0.60,
            percent_dc_charged=0.20,
            percent_level2_charged=0.20,
        ),
    }


def create_tax_incentives() -> dict[str, TaxIncentives]:
    """Create sample tax incentive scenarios."""

    return {
        "federal_only": TaxIncentives(
            federal_tax_credit=7_500,
            state_tax_credit=0,
            local_rebate=0,
            utility_rebate=0,
        ),
        "federal_and_state": TaxIncentives(
            federal_tax_credit=7_500,
            state_tax_credit=3_500,
            local_rebate=0,
            utility_rebate=500,
        ),
        "california": TaxIncentives(
            federal_tax_credit=7_500,
            state_tax_credit=2_000,
            local_rebate=0,
            utility_rebate=1_000,
        ),
    }


def create_traditional_vehicles() -> dict[str, dict[str, float]]:
    """Create traditional vehicle specifications for comparison."""

    return {
        "toyota_camry": {
            "name": "Toyota Camry",
            "initial_cost": 28_000,
            "mpg": 32,
            "fuel_price": 3.50,
            "maintenance_per_mile": 0.08,
            "insurance_per_year": 1_300,
            "registration_per_year": 250,
            "monthly_payment": 450,
        },
        "honda_civic": {
            "name": "Honda Civic",
            "initial_cost": 26_000,
            "mpg": 33,
            "fuel_price": 3.50,
            "maintenance_per_mile": 0.07,
            "insurance_per_year": 1_250,
            "registration_per_year": 230,
            "monthly_payment": 400,
        },
    }


def create_hybrid_vehicles() -> dict[str, dict[str, float]]:
    """Create hybrid vehicle specifications for comparison."""

    return {
        "toyota_prius": {
            "name": "Toyota Prius",
            "initial_cost": 28_000,
            "mpg_combined": 56,
            "fuel_price": 3.50,
            "maintenance_per_mile": 0.05,
            "insurance_per_year": 1_200,
            "registration_per_year": 250,
            "monthly_payment": 450,
        },
        "honda_insight": {
            "name": "Honda Insight",
            "initial_cost": 27_000,
            "mpg_combined": 53,
            "fuel_price": 3.50,
            "maintenance_per_mile": 0.05,
            "insurance_per_year": 1_150,
            "registration_per_year": 230,
            "monthly_payment": 420,
        },
    }


def example_ev_tco_analysis() -> dict[str, object]:
    """Example: Calculate TCO for a specific EV."""

    print("\n" + "=" * 80)
    print("EXAMPLE 1: Tesla Model 3 TCO Analysis")
    print("=" * 80)

    vehicles = create_sample_evs()
    financing = create_sample_financing()
    energy_params = create_sample_energy_params()
    incentives = create_tax_incentives()

    analyzer = EVTotalCostOfOwnershipAnalyzer(
        vehicle=vehicles["tesla_model_3"],
        financing=financing["standard_loan"],
        energy_params=energy_params["california"],
        incentives=incentives["federal_and_state"],
    )

    tco = analyzer.calculate_comprehensive_tco(years=10)

    summary = tco["summary"]
    print(f"\nVehicle: {summary['vehicle_name']}")
    print(f"Initial Purchase Price: ${summary['initial_cost']:,.2f}")
    print(f"Total Tax Incentives: ${summary['total_incentives']:,.2f}")
    print(f"Net Initial Cost: ${summary['net_initial_cost']:,.2f}")
    print(
        f"\nOwnership Period: {summary['financing_years']} years of financing + "
        f"{10 - summary['financing_years']} years ownership"
    )
    print(f"Total Miles Driven: {summary['total_miles_driven']:,.0f}")
    print(f"\nTotal Ownership Cost: ${summary['total_ownership_cost']:,.2f}")
    print(f"Final Residual Value: ${summary['final_residual_value']:,.2f}")
    print(f"Net Ownership Cost: ${summary['net_ownership_cost']:,.2f}")
    print(f"Cost Per Mile: ${summary['cost_per_mile']:.3f}")

    print("\n" + "-" * 80)
    print("ANNUAL COST BREAKDOWN")
    print("-" * 80)
    annual_df = pd.DataFrame(tco["annual_details"])
    print(
        annual_df[
            [
                "year",
                "financing_cost",
                "operating_cost",
                "energy_cost",
                "total_annual_cost",
                "cost_per_mile",
            ]
        ].to_string(index=False)
    )

    return tco


def example_ev_comparison() -> dict[str, object]:
    """Example: Compare EV with traditional and hybrid vehicles."""

    print("\n" + "=" * 80)
    print("EXAMPLE 2: EV vs Traditional vs Hybrid Comparison")
    print("=" * 80)

    vehicles = create_sample_evs()
    energy_params = create_sample_energy_params()
    traditional = create_traditional_vehicles()
    hybrid = create_hybrid_vehicles()

    analyzer = EVComparisonAnalyzer()

    comparison = analyzer.compare_vehicles(
        ev=vehicles["tesla_model_3"],
        traditional=traditional["toyota_camry"],
        hybrid=hybrid["toyota_prius"],
        years=10,
        annual_miles=12_000,
        energy_params=energy_params["california"],
    )

    print("\nComparison Summary:")
    print(f"EV: {comparison['vehicles_compared']['EV']}")
    print(f"Traditional: {comparison['vehicles_compared']['Traditional']}")
    print(f"Hybrid: {comparison['vehicles_compared']['Hybrid']}")
    print(f"Analysis Period: {comparison['years_analyzed']} years")
    print(f"Annual Miles: {comparison['annual_miles']:,}")

    print("\n" + "-" * 80)
    print("EV vs TRADITIONAL VEHICLE")
    print("-" * 80)
    if "ev_vs_traditional" in comparison:
        savings = comparison["ev_vs_traditional"]
        print(f"EV Net Cost: ${comparison['ev']['net_ownership_cost']:,.2f}")
        print(f"Traditional Net Cost: ${comparison['traditional']['net_cost']:,.2f}")
        print(f"Total Savings: ${savings['total_savings']:,.2f}")
        print(f"Annual Savings: ${savings['annual_savings']:,.2f}")
        print(f"Price Premium: ${savings['price_premium']:,.2f}")
        if savings['payback_period_years']:
            print(f"Payback Period: {savings['payback_period_years']:.1f} years")
        print(f"Savings Percentage: {savings['savings_percent']:.1f}%")

    print("\n" + "-" * 80)
    print("EV vs HYBRID VEHICLE")
    print("-" * 80)
    if "ev_vs_hybrid" in comparison:
        savings = comparison["ev_vs_hybrid"]
        print(f"EV Net Cost: ${comparison['ev']['net_ownership_cost']:,.2f}")
        print(f"Hybrid Net Cost: ${comparison['hybrid']['net_cost']:,.2f}")
        print(f"Total Savings: ${savings['total_savings']:,.2f}")
        print(f"Annual Savings: ${savings['annual_savings']:,.2f}")
        print(f"Price Premium: ${savings['price_premium']:,.2f}")
        if savings['payback_period_years']:
            print(f"Payback Period: {savings['payback_period_years']:.1f} years")
        print(f"Savings Percentage: {savings['savings_percent']:.1f}%")

    return comparison


def example_sensitivity_analysis() -> dict[str, object]:
    """Example: Perform sensitivity analysis on EV model."""

    print("\n" + "=" * 80)
    print("EXAMPLE 3: Sensitivity Analysis - Impact of Electricity Rates")
    print("=" * 80)

    vehicles = create_sample_evs()
    financing = create_sample_financing()
    energy_params = create_sample_energy_params()
    incentives = create_tax_incentives()

    analyzer = EVTotalCostOfOwnershipAnalyzer(
        vehicle=vehicles["tesla_model_3"],
        financing=financing["standard_loan"],
        energy_params=energy_params["california"],
        incentives=incentives["federal_and_state"],
    )

    sensitivity = EVSensitivityAnalyzer(analyzer)

    result = sensitivity.sensitivity_analysis(
        variable="electricity_rate",
        variation_percent=20,
        years=10,
    )

    print(f"\nVariable: {result['variable']}")
    print(f"Base Value: ${result['base_value']:.3f}/kWh")
    print(f"Base Cost Per Mile: ${result['base_cost_per_mile']:.3f}")

    print("\n" + "-" * 80)
    print("SCENARIO ANALYSIS")
    print("-" * 80)
    scenarios_df = pd.DataFrame(result["scenarios"])
    print(
        scenarios_df[
            ["factor", "change_percent", "new_value", "cost_per_mile", "impact_percent"]
        ].to_string(index=False)
    )

    return result


def example_regional_analysis() -> pd.DataFrame:
    """Example: Compare EVs across different regions."""

    print("\n" + "=" * 80)
    print("EXAMPLE 4: Regional Analysis - Cost of Ownership by Region")
    print("=" * 80)

    vehicles = create_sample_evs()
    financing = create_sample_financing()
    energy_params_all = create_sample_energy_params()
    incentives_all = create_tax_incentives()

    regions = {
        "California": {
            "energy": energy_params_all["california"],
            "incentives": incentives_all["california"],
        },
        "Texas": {
            "energy": energy_params_all["texas"],
            "incentives": incentives_all["federal_only"],
        },
        "New York": {
            "energy": energy_params_all["new_york"],
            "incentives": incentives_all["federal_and_state"],
        },
    }

    results = []

    for region_name, params in regions.items():
        analyzer = EVTotalCostOfOwnershipAnalyzer(
            vehicle=vehicles["tesla_model_3"],
            financing=financing["standard_loan"],
            energy_params=params["energy"],
            incentives=params["incentives"],
        )

        tco = analyzer.calculate_comprehensive_tco(years=10)

        results.append(
            {
                "Region": region_name,
                "Electricity Rate ($/kWh)": params["energy"].electricity_rate_per_kwh,
                "Annual Miles": params["energy"].annual_miles_driven,
                "Net Cost": tco["summary"]["net_ownership_cost"],
                "Cost Per Mile": tco["summary"]["cost_per_mile"],
                "Incentives": tco["summary"]["total_incentives"],
            }
        )

    results_df = pd.DataFrame(results)
    print("\n" + results_df.to_string(index=False))

    return results_df


def run_all_examples() -> None:
    """Run all example analyses."""

    try:
        example_ev_tco_analysis()
        example_ev_comparison()
        example_sensitivity_analysis()
        example_regional_analysis()

        print("\n" + "=" * 80)
        print("ALL EXAMPLES COMPLETED SUCCESSFULLY")
        print("=" * 80)
    except Exception as exc:  # pragma: no cover - demonstration helper
        print(f"\nError running examples: {exc}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    run_all_examples()
