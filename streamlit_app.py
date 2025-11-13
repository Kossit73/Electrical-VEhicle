"""Streamlit application for exploring EV financial scenarios."""

from dataclasses import replace
from pathlib import Path
import sys
from typing import Dict, Optional

import pandas as pd
import streamlit as st

try:  # pragma: no cover - optional for charting
    import altair as alt
except Exception:  # pragma: no cover - graceful fallback when Altair missing
    alt = None


# Ensure the repository's ``src`` directory is on ``sys.path`` so the packaged
# ``ev_model`` module is importable when the app is executed with ``streamlit``
# from the project root or an arbitrary working directory. This mirrors the
# layout used by the test suite and avoids requiring an editable install before
# running the dashboard locally.
_SRC_PATH = Path(__file__).resolve().parent / "src"
if _SRC_PATH.exists():  # pragma: no cover - filesystem guard for deployment
    _src_str = str(_SRC_PATH)
    if _src_str not in sys.path:
        sys.path.insert(0, _src_str)


from ev_model import (
    EVComparisonAnalyzer,
    EVSensitivityAnalyzer,
    EVTotalCostOfOwnershipAnalyzer,
    EVVehicleSpecs,
    EnergyParameters,
    TaxIncentives,
    VehicleFinancing,
)
from scripts.examples import (
    create_hybrid_vehicles,
    create_sample_energy_params,
    create_sample_evs,
    create_sample_financing,
    create_tax_incentives,
    create_traditional_vehicles,
)

st.set_page_config(
    page_title="EV Financial Model",
    page_icon="🚗",
    layout="wide",
)

st.title("🚗 Electric Vehicle Financial Model")
st.write(
    "Analyse the total cost of ownership (TCO) of electric vehicles, explore"
    " annual cost breakdowns, and benchmark EVs against traditional or hybrid"
    " alternatives. Adjust the assumptions in the sidebar to tailor the"
    " scenario to your needs."
)


@st.cache_data
def load_samples():
    return {
        "evs": create_sample_evs(),
        "financing": create_sample_financing(),
        "energy": create_sample_energy_params(),
        "incentives": create_tax_incentives(),
        "traditional": create_traditional_vehicles(),
        "hybrid": create_hybrid_vehicles(),
    }


SAMPLES = load_samples()


def _format_currency(value: float) -> str:
    return f"$ {value:,.0f}"


with st.sidebar:
    st.header("Scenario configuration")

    # Vehicle selection -----------------------------------------------------
    sample_evs = SAMPLES["evs"]
    vehicle_options = list(sample_evs.keys()) + ["Custom"]
    vehicle_key = st.selectbox(
        "Vehicle",
        vehicle_options,
        format_func=lambda key: sample_evs[key].name if key in sample_evs else key,
    )

    if vehicle_key == "Custom":
        st.subheader("Custom vehicle")
        vehicle_name = st.text_input("Model name", value="Custom EV")
        purchase_price = st.number_input("Purchase price", min_value=10_000.0, value=45_000.0, step=1_000.0)
        battery_capacity = st.number_input(
            "Battery capacity (kWh)", min_value=10.0, value=60.0, step=1.0
        )
        epa_range = st.number_input("EPA range (miles)", min_value=100.0, value=250.0, step=10.0)
        efficiency = st.number_input(
            "Efficiency (kWh/mile)", min_value=0.1, max_value=0.6, value=0.24, step=0.01
        )
        warranty_years = st.slider("Battery warranty (years)", min_value=3, max_value=12, value=8)
        warranty_miles = st.number_input(
            "Warranty miles", min_value=50_000.0, value=120_000.0, step=5_000.0
        )
        battery_replacement = st.number_input(
            "Battery replacement cost", min_value=0.0, value=7_000.0, step=500.0
        )
        registration_fee = st.number_input(
            "Annual registration fee", min_value=0.0, value=250.0, step=25.0
        )
        insurance_cost = st.number_input(
            "Annual insurance cost", min_value=0.0, value=1_200.0, step=50.0
        )
        maintenance_cost = st.number_input(
            "Maintenance cost per mile", min_value=0.0, value=0.02, step=0.005, format="%.3f"
        )
        vehicle = EVVehicleSpecs(
            name=vehicle_name,
            purchase_price=purchase_price,
            battery_capacity_kwh=battery_capacity,
            epa_range_miles=epa_range,
            efficiency_kwh_per_mile=efficiency,
            warranty_years=warranty_years,
            warranty_miles=warranty_miles,
            battery_replacement_cost=battery_replacement,
            annual_registration_fee=registration_fee,
            annual_insurance_cost=insurance_cost,
            maintenance_cost_per_mile=maintenance_cost,
        )
    else:
        vehicle = replace(sample_evs[vehicle_key])

    # Financing -------------------------------------------------------------
    st.subheader("Financing")
    financing_options = {"Default (20% down, 5y, 4.5%)": None}
    financing_options.update(SAMPLES["financing"])
    financing_key = st.selectbox(
        "Financing option",
        list(financing_options.keys()) + ["Custom"],
    )

    financing: Optional[VehicleFinancing]
    if financing_key == "Custom":
        loan_amount = st.number_input(
            "Loan amount", min_value=0.0, value=max(vehicle.purchase_price * 0.8, 0.0), step=1_000.0
        )
        down_payment = st.number_input(
            "Down payment", min_value=0.0, value=vehicle.purchase_price - loan_amount, step=1_000.0
        )
        loan_term = st.slider("Loan term (years)", min_value=1, max_value=10, value=5)
        interest_rate = st.number_input(
            "Interest rate (APR)", min_value=0.0, max_value=0.2, value=0.045, step=0.005, format="%.3f"
        )
        financing = VehicleFinancing(
            loan_amount=loan_amount,
            down_payment=down_payment,
            loan_term_years=loan_term,
            annual_interest_rate=interest_rate,
        )
    else:
        selected_financing = financing_options.get(financing_key)
        financing = replace(selected_financing) if selected_financing else None

    # Energy parameters -----------------------------------------------------
    st.subheader("Energy & driving")
    energy_presets = list(SAMPLES["energy"].keys()) + ["Custom"]
    energy_key = st.selectbox("Energy scenario", energy_presets)

    if energy_key == "Custom":
        electricity_rate = st.number_input(
            "Electricity rate ($/kWh)", min_value=0.05, max_value=0.6, value=0.14, step=0.01
        )
        annual_miles = st.number_input(
            "Annual miles driven", min_value=2_000.0, max_value=40_000.0, value=12_000.0, step=500.0
        )
        home_share = st.slider("Home charging share", min_value=0.0, max_value=1.0, value=0.7, step=0.05)
        dc_share = st.slider(
            "DC fast charging share",
            min_value=0.0,
            max_value=1.0 - home_share,
            value=0.1,
            step=0.05,
        )
        level2_share = max(0.0, 1.0 - home_share - dc_share)
        st.caption(
            f"Level 2 charging share automatically adjusted to {level2_share:.0%}"
        )
        energy_params = EnergyParameters(
            electricity_rate_per_kwh=electricity_rate,
            home_charging_efficiency=0.90,
            dc_fast_charging_efficiency=0.80,
            annual_miles_driven=annual_miles,
            percent_home_charged=home_share,
            percent_dc_charged=dc_share,
            percent_level2_charged=level2_share,
        )
    else:
        energy_params = replace(SAMPLES["energy"][energy_key])

    # Incentives ------------------------------------------------------------
    st.subheader("Incentives")
    incentive_options = list(SAMPLES["incentives"].keys()) + ["None", "Custom"]
    incentive_key = st.selectbox("Tax incentives", incentive_options)

    incentives: Optional[TaxIncentives]
    if incentive_key == "None":
        incentives = None
    elif incentive_key == "Custom":
        federal_credit = st.number_input("Federal tax credit", min_value=0.0, value=7_500.0, step=500.0)
        state_credit = st.number_input("State credit", min_value=0.0, value=2_000.0, step=250.0)
        local_rebate = st.number_input("Local rebate", min_value=0.0, value=0.0, step=250.0)
        utility_rebate = st.number_input("Utility rebate", min_value=0.0, value=500.0, step=250.0)
        incentives = TaxIncentives(
            federal_tax_credit=federal_credit,
            state_tax_credit=state_credit,
            local_rebate=local_rebate,
            utility_rebate=utility_rebate,
        )
    else:
        incentives = replace(SAMPLES["incentives"][incentive_key])

    years = st.slider("Analysis period (years)", min_value=3, max_value=20, value=10)

    show_comparison = st.checkbox("Compare with ICE / Hybrid", value=True)
    show_sensitivity = st.checkbox("Run sensitivity analysis", value=True)

# ---------------------------------------------------------------------------
# Core analysis

try:
    analyzer = EVTotalCostOfOwnershipAnalyzer(
        vehicle=vehicle,
        financing=financing,
        energy_params=energy_params,
        incentives=incentives,
    )
    tco_result = analyzer.calculate_comprehensive_tco(years=years)
except Exception as exc:  # pragma: no cover - user input errors surfaced in UI
    st.error(f"Unable to calculate TCO with the current inputs: {exc}")
    st.stop()

summary = tco_result["summary"]
st.subheader("Summary")
summary_cols = st.columns(4)
summary_cols[0].metric("Net ownership cost", _format_currency(summary["net_ownership_cost"]))
summary_cols[1].metric("Cost per mile", f"$ {summary['cost_per_mile']:.3f}")
summary_cols[2].metric("Total incentives", _format_currency(summary["total_incentives"]))
summary_cols[3].metric("Residual value", _format_currency(summary["final_residual_value"]))

st.caption(
    "Net ownership cost includes acquisition costs, annual operating expenses,"
    " and subtracts the residual value after the analysis period."
)

annual_df = pd.DataFrame(tco_result["annual_details"]).set_index("year")
operating_df = pd.DataFrame(tco_result["operating_details"])
energy_df = pd.DataFrame(tco_result["energy_details"])
depreciation_df = pd.DataFrame(tco_result["depreciation_details"])

if alt is not None and not annual_df.empty:
    melted = (
        annual_df[["financing_cost", "operating_cost", "energy_cost"]]
        .reset_index()
        .melt("year", var_name="category", value_name="cost")
    )
    cost_chart = (
        alt.Chart(melted)
        .mark_bar()
        .encode(
            x=alt.X("year:O", title="Year"),
            y=alt.Y("cost:Q", title="Annual cost (USD)"),
            color=alt.Color("category:N", title="Category"),
            tooltip=["year", "category", alt.Tooltip("cost:Q", format=",.0f")],
        )
        .properties(title="Annual cost breakdown")
    )
    cumulative_chart = (
        alt.Chart(annual_df.reset_index())
        .mark_line(point=True)
        .encode(
            x=alt.X("year:O", title="Year"),
            y=alt.Y("cumulative_cost:Q", title="Cumulative cost (USD)"),
            tooltip=["year", alt.Tooltip("cumulative_cost:Q", format=",.0f")],
        )
        .properties(title="Cumulative ownership cost")
    )
    st.altair_chart(cost_chart, use_container_width=True)
    st.altair_chart(cumulative_chart, use_container_width=True)
else:
    st.line_chart(annual_df["cumulative_cost"])  # pragma: no cover - Altair fallback

with st.expander("Annual cash flow details", expanded=False):
    st.dataframe(annual_df)

with st.expander("Operating cost schedule", expanded=False):
    st.dataframe(operating_df)

with st.expander("Energy usage & charging mix", expanded=False):
    st.dataframe(energy_df)

with st.expander("Depreciation schedule", expanded=False):
    st.dataframe(depreciation_df)

# ---------------------------------------------------------------------------
# Comparison analysis
if show_comparison:
    st.subheader("Comparison against other powertrains")
    traditional_options: Dict[str, Optional[Dict[str, float]]] = {"None": None, **SAMPLES["traditional"]}
    hybrid_options: Dict[str, Optional[Dict[str, float]]] = {"None": None, **SAMPLES["hybrid"]}

    compare_cols = st.columns(2)
    with compare_cols[0]:
        traditional_key = st.selectbox(
            "Traditional vehicle",
            list(traditional_options.keys()),
            index=1 if len(traditional_options) > 1 else 0,
        )
    with compare_cols[1]:
        hybrid_key = st.selectbox(
            "Hybrid vehicle",
            list(hybrid_options.keys()),
            index=1 if len(hybrid_options) > 1 else 0,
        )

    traditional_vehicle = traditional_options[traditional_key]
    hybrid_vehicle = hybrid_options[hybrid_key]

    comparison_analyzer = EVComparisonAnalyzer()
    comparison_result = comparison_analyzer.compare_vehicles(
        ev=vehicle,
        traditional=traditional_vehicle,
        hybrid=hybrid_vehicle,
        years=years,
        annual_miles=energy_params.annual_miles_driven,
        energy_params=energy_params,
    )

    comparison_rows: list[Dict[str, float]] = []
    comparison_rows.append(
        {
            "Vehicle": comparison_result["vehicles_compared"]["EV"],
            "Net cost": summary["net_ownership_cost"],
            "Cost per mile": summary["cost_per_mile"],
            "Residual value": summary["final_residual_value"],
        }
    )

    if traditional_vehicle:
        traditional_summary = comparison_result["traditional"]
        comparison_rows.append(
            {
                "Vehicle": comparison_result["vehicles_compared"]["Traditional"],
                "Net cost": traditional_summary["net_cost"],
                "Cost per mile": traditional_summary["total_annual_cost"]
                / energy_params.annual_miles_driven,
                "Residual value": traditional_summary["residual_value"],
            }
        )

    if hybrid_vehicle:
        hybrid_summary = comparison_result["hybrid"]
        comparison_rows.append(
            {
                "Vehicle": comparison_result["vehicles_compared"]["Hybrid"],
                "Net cost": hybrid_summary["net_cost"],
                "Cost per mile": hybrid_summary["total_annual_cost"] / energy_params.annual_miles_driven,
                "Residual value": hybrid_summary["residual_value"],
            }
        )

    comparison_df = pd.DataFrame(comparison_rows)
    st.dataframe(
        comparison_df.style.format(
            {
                "Net cost": "$ {:,.0f}",
                "Cost per mile": "$ {:.3f}",
                "Residual value": "$ {:,.0f}",
            }
        )
    )

    savings_cols = st.columns(2)
    if "ev_vs_traditional" in comparison_result and traditional_vehicle:
        savings = comparison_result["ev_vs_traditional"]
        payback = (
            f"Payback: {savings['payback_period_years']:.1f} years"
            if savings["payback_period_years"]
            else "No payback"
        )
        savings_cols[0].metric(
            "Savings vs traditional",
            _format_currency(savings["total_savings"]),
            payback,
        )
    if "ev_vs_hybrid" in comparison_result and hybrid_vehicle:
        savings = comparison_result["ev_vs_hybrid"]
        payback = (
            f"Payback: {savings['payback_period_years']:.1f} years"
            if savings["payback_period_years"]
            else "No payback"
        )
        savings_cols[1].metric(
            "Savings vs hybrid",
            _format_currency(savings["total_savings"]),
            payback,
        )

# ---------------------------------------------------------------------------
# Sensitivity analysis
if show_sensitivity:
    st.subheader("Sensitivity analysis")
    variable = st.selectbox(
        "Variable",
        options=["electricity_rate", "annual_miles", "purchase_price", "battery_cost"],
        format_func=lambda value: value.replace("_", " ").title(),
    )
    variation = st.slider("Variation ±%", min_value=5, max_value=50, value=20, step=5)

    try:
        sensitivity_analyzer = EVSensitivityAnalyzer(analyzer)
        sensitivity_result = sensitivity_analyzer.sensitivity_analysis(
            variable=variable,
            variation_percent=variation,
            years=years,
        )
    except Exception as exc:  # pragma: no cover - input validation surfaced in UI
        st.warning(f"Sensitivity analysis could not be completed: {exc}")
    else:
        scenarios_df = pd.DataFrame(sensitivity_result["scenarios"])
        st.write(
            f"Base {variable.replace('_', ' ')}: {sensitivity_result['base_value']:.3f}"
            f" → Base cost per mile: $ {sensitivity_result['base_cost_per_mile']:.3f}"
        )
        st.dataframe(
            scenarios_df[["change_percent", "new_value", "cost_per_mile", "impact_percent"]]
            .rename(
                columns={
                    "change_percent": "Δ %",
                    "new_value": "New value",
                    "cost_per_mile": "Cost per mile",
                    "impact_percent": "Impact %",
                }
            )
            .style.format(
                {
                    "Δ %": "{:.0f}%",
                    "New value": "{:.3f}",
                    "Cost per mile": "$ {:.3f}",
                    "Impact %": "{:+.1f}%",
                }
            )
        )

        if alt is not None:
            sensitivity_chart = (
                alt.Chart(scenarios_df)
                .mark_line(point=True)
                .encode(
                    x=alt.X("change_percent:Q", title="Change vs base (%)"),
                    y=alt.Y("cost_per_mile:Q", title="Cost per mile"),
                    tooltip=["factor", "cost_per_mile", "impact_percent"],
                )
                .properties(title="Cost per mile impact")
            )
            st.altair_chart(sensitivity_chart, use_container_width=True)

st.success("Configuration complete. Adjust the inputs to explore alternative scenarios.")
