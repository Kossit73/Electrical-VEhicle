# Electric Vehicle (EV) Financial Model

## Overview

A comprehensive financial model for analyzing the total cost of ownership (TCO) for electric vehicles. This model integrates vehicle acquisition, operating costs, energy consumption, depreciation, and provides comparisons with traditional and hybrid vehicles.

## Features

### 1. **Vehicle Acquisition Analysis**
- Purchase price calculation
- Financing options (loans, leases)
- Down payment and monthly payment calculations
- Tax incentives and rebates (federal, state, local, utility)
- Registration and insurance costs

### 2. **Operating Costs**
- Annual maintenance and repair costs (significantly lower for EVs)
- Tire replacement costs (extended life due to regenerative braking)
- Battery degradation monitoring and replacement reserves
- Warranty coverage analysis
- Year-by-year cost projections with inflation

### 3. **Energy Costs**
- Multi-method charging support (home, DC fast charging, Level 2)
- Electricity rate variability by region
- Charging efficiency calculations
- Battery capacity and range analysis
- Energy cost per mile tracking
- Comparison with traditional fuel costs

### 4. **Depreciation Analysis**
Three depreciation methods:
- **Straight-Line**: Equal annual depreciation
- **Declining Balance**: Faster initial depreciation, then slower
- **Market-Based**: Empirical EV depreciation curves (recommended for EVs)
  - Year 1: 18% (steep due to tax credits used)
  - Year 2-3: 10% annually
  - Year 4-5: 8% annually
  - Year 6+: 5% annually

### 5. **Total Cost of Ownership (TCO)**
- Comprehensive cost aggregation
- Year-by-year breakdown
- Residual value calculation
- Cost per mile analysis
- Cumulative cost tracking

### 6. **Vehicle Comparison**
- EV vs. Traditional vehicle comparison
- EV vs. Hybrid vehicle comparison
- Payback period analysis
- Savings calculation and visualization
- Annual savings tracking

### 7. **Sensitivity Analysis**
Test impact of variable changes:
- Electricity rates (±20%)
- Annual miles driven (±20%)
- Purchase price (±20%)
- Battery replacement cost (±20%)

## Usage

### Basic Installation

```python
from ev_financial_model import (
    EVVehicleSpecs,
    VehicleFinancing,
    EnergyParameters,
    TaxIncentives,
    EVTotalCostOfOwnershipAnalyzer,
)
```

### Example 1: Calculate EV TCO

```python
# Define vehicle
vehicle = EVVehicleSpecs(
    name='Tesla Model 3',
    purchase_price=46995,
    battery_capacity_kwh=54,
    epa_range_miles=263,
    efficiency_kwh_per_mile=0.205,
    warranty_years=8,
    warranty_miles=120000,
    battery_replacement_cost=7000,
    annual_registration_fee=250,
    annual_insurance_cost=1200,
    maintenance_cost_per_mile=0.02,
)

# Define financing
financing = VehicleFinancing(
    loan_amount=35000,
    down_payment=10000,
    loan_term_years=5,
    annual_interest_rate=0.045,
)

# Define energy parameters
energy_params = EnergyParameters(
    electricity_rate_per_kwh=0.14,
    home_charging_efficiency=0.90,
    dc_fast_charging_efficiency=0.80,
    annual_miles_driven=12000,
    percent_home_charged=0.70,
    percent_dc_charged=0.10,
    percent_level2_charged=0.20,
)

# Define incentives
incentives = TaxIncentives(
    federal_tax_credit=7500,
    state_tax_credit=3500,
    local_rebate=0,
    utility_rebate=500,
)

# Calculate TCO
analyzer = EVTotalCostOfOwnershipAnalyzer(
    vehicle=vehicle,
    financing=financing,
    energy_params=energy_params,
    incentives=incentives,
)

tco = analyzer.calculate_comprehensive_tco(years=10)

# Access results
summary = tco['summary']
print(f"Net Ownership Cost: ${summary['net_ownership_cost']:,.2f}")
print(f"Cost Per Mile: ${summary['cost_per_mile']:.3f}")
```

### Example 2: Compare with Traditional Vehicle

```python
from ev_financial_model import EVComparisonAnalyzer

traditional_vehicle = {
    'name': 'Toyota Camry',
    'initial_cost': 28000,
    'mpg': 32,
    'fuel_price': 3.50,
    'maintenance_per_mile': 0.08,
    'insurance_per_year': 1300,
    'registration_per_year': 250,
    'monthly_payment': 450,
}

comparison = EVComparisonAnalyzer()
result = comparison.compare_vehicles(
    ev=vehicle,
    traditional=traditional_vehicle,
    years=10,
    annual_miles=12000,
)

# View savings
savings = result['ev_vs_traditional']
print(f"Total Savings: ${savings['total_savings']:,.2f}")
print(f"Payback Period: {savings['payback_period_years']:.1f} years")
```

### Example 3: Sensitivity Analysis

```python
from ev_financial_model import EVSensitivityAnalyzer

sensitivity = EVSensitivityAnalyzer(analyzer)
result = sensitivity.sensitivity_analysis(
    variable='electricity_rate',
    variation_percent=20,
    years=10,
)

# View impact of electricity rate changes
for scenario in result['scenarios']:
    print(f"Rate: ${scenario['new_value']:.3f}/kWh → "
          f"Cost/Mile: ${scenario['cost_per_mile']:.3f} "
          f"(Impact: {scenario['impact_percent']:+.1f}%)")
```

## API Endpoints

### POST `/ev/calculate-tco`
Calculate total cost of ownership for an EV.

**Request:**
```json
{
  "vehicle": {
    "name": "Tesla Model 3",
    "purchase_price": 46995,
    "battery_capacity_kwh": 54,
    "epa_range_miles": 263,
    "efficiency_kwh_per_mile": 0.205,
    "warranty_years": 8,
    "warranty_miles": 120000,
    "battery_replacement_cost": 7000,
    "annual_registration_fee": 250,
    "annual_insurance_cost": 1200,
    "maintenance_cost_per_mile": 0.02
  },
  "financing": {
    "loan_amount": 35000,
    "down_payment": 10000,
    "loan_term_years": 5,
    "annual_interest_rate": 0.045
  },
  "energy_parameters": {
    "electricity_rate_per_kwh": 0.14,
    "home_charging_efficiency": 0.90,
    "dc_fast_charging_efficiency": 0.80,
    "annual_miles_driven": 12000,
    "percent_home_charged": 0.70,
    "percent_dc_charged": 0.10,
    "percent_level2_charged": 0.20
  },
  "tax_incentives": {
    "federal_tax_credit": 7500,
    "state_tax_credit": 3500,
    "local_rebate": 0,
    "utility_rebate": 500
  },
  "years": 10
}
```

**Response:**
```json
{
  "status": "success",
  "summary": {
    "vehicle_name": "Tesla Model 3",
    "initial_cost": 46995,
    "net_initial_cost": 37995,
    "total_incentives": 9000,
    "total_ownership_cost": 67234.56,
    "total_miles_driven": 120000,
    "final_residual_value": 15234.67,
    "net_ownership_cost": 52000,
    "cost_per_mile": 0.433
  },
  "annual_breakdown": [...],
  "operating_details": [...],
  "energy_details": [...],
  "depreciation_details": [...]
}
```

### POST `/ev/compare-vehicles`
Compare EV with traditional and hybrid vehicles.

### POST `/ev/sensitivity-analysis`
Perform sensitivity analysis on key variables.

**Variables:**
- `electricity_rate`: Impact of electricity price changes
- `annual_miles`: Impact of driving patterns
- `purchase_price`: Impact of vehicle price
- `battery_cost`: Impact of battery replacement cost

### POST `/ev/depreciation-schedule`
Calculate vehicle depreciation using specified method.

**Methods:**
- `straight_line`
- `declining_balance`
- `market_based`

### GET `/ev/sample-vehicles`
Get sample EV vehicle specifications.

### GET `/ev/regional-rates`
Get sample electricity rates by region.

## Key Assumptions

### EV Operating Costs
- **Maintenance**: $0.02/mile (vs. $0.08/mile for traditional vehicles)
- **Tire Life**: ~50,000 miles (extended due to regenerative braking)
- **Battery Warranty**: 8-10 years, 100,000-120,000 miles
- **Battery Degradation**: 5% annually after warranty

### Electricity Rates (Regional Examples)
- California: $0.18/kWh
- Texas: $0.11/kWh
- New York: $0.16/kWh
- Washington: $0.10/kWh

### Charging Efficiency
- Home Charging: 90% (12V/240V)
- DC Fast Charging: 80% (high-speed charging losses)
- Level 2: 90% (240V AC charging)

### EV Depreciation (Market-Based)
- Year 1: 18% (steep due to tax credits used)
- Years 2-3: 10% annually
- Years 4-5: 8% annually
- Years 6+: 5% annually
- High mileage adjustment: +5% per 100,000 miles above 150,000

## Data Requirements

### Vehicle Specifications
- Purchase price
- Battery capacity (kWh)
- EPA range (miles)
- Efficiency (kWh/mile)
- Warranty terms
- Maintenance costs
- Insurance costs
- Registration fees

### Financing Parameters
- Loan amount
- Down payment
- Loan term (years)
- Interest rate
- Payment frequency

### Energy Parameters
- Electricity rate ($/kWh)
- Annual miles driven
- Charging method mix
- Charging efficiency

### Incentives
- Federal tax credits
- State/local credits
- Rebates
