# React + Streamlit integration blueprint

This guide explains how to layer a React single-page application (SPA) on top of the existing Python EV financial model while still keeping the Streamlit dashboard available for Python-first workflows.

## Architecture overview
- **FastAPI layer (Python):** Exposes the EV model via JSON endpoints defined in `ev_model.api.ev_router`, now mounted in `scripts/api_server.py`. React calls these endpoints for calculations.
- **React SPA (JavaScript/TypeScript):** Presents forms, charts, and scenario lists. It posts payloads that mirror the model dataclasses (`EVVehicleSpecs`, `VehicleFinancing`, `EnergyParameters`, `TaxIncentives`).
- **Streamlit app (Python):** Remains available at `streamlit_app.py` for internal analytics or demo needs; it uses the same model classes directly without the API hop.

## Start the Python API for React
1. Install the optional API dependencies:
   ```bash
   pip install fastapi uvicorn "pydantic>=1.10,<3"
   ```
2. Run the FastAPI app (includes CORS for local React dev ports):
   ```bash
   uvicorn scripts.api_server:app --reload --port 8000
   ```
3. Explore docs at `http://localhost:8000/docs` and sample payloads at `http://localhost:8000/sample-payloads`.

## Seed data you can reuse in React
- `GET /sample-payloads` returns:
  - A ready-to-submit TCO request
  - Default comparison payloads (EV vs. traditional / hybrid)
  - A base sensitivity payload
- The response mirrors the request bodies expected by `/ev/calculate-tco`, `/ev/compare-vehicles`, and `/ev/sensitivity-analysis`.

## React data layer example (TypeScript)
Create a minimal client that matches the Pydantic schemas:
```ts
// src/api/evClient.ts
export type Vehicle = {
  name: string;
  purchase_price: number;
  battery_capacity_kwh: number;
  epa_range_miles: number;
  efficiency_kwh_per_mile: number;
  warranty_years: number;
  warranty_miles: number;
  battery_replacement_cost: number;
  annual_registration_fee: number;
  annual_insurance_cost: number;
  maintenance_cost_per_mile: number;
};

export type Financing = {
  loan_amount: number;
  down_payment: number;
  loan_term_years: number;
  annual_interest_rate: number;
};

export type EnergyParameters = {
  electricity_rate_per_kwh: number;
  home_charging_efficiency: number;
  dc_fast_charging_efficiency: number;
  annual_miles_driven: number;
  percent_home_charged: number;
  percent_dc_charged: number;
  percent_level2_charged: number;
};

export type TaxIncentives = {
  federal_tax_credit: number;
  state_tax_credit: number;
  local_rebate: number;
  utility_rebate: number;
};

export async function calculateTco(payload: {
  vehicle: Vehicle;
  financing?: Financing;
  energy_parameters: EnergyParameters;
  tax_incentives?: TaxIncentives;
  years?: number;
}) {
  const res = await fetch("http://localhost:8000/ev/calculate-tco", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`TCO request failed: ${res.status}`);
  return res.json();
}
```

## React UI wiring example (Vite + React)
```tsx
// src/components/TcoForm.tsx
import { useEffect, useState } from "react";
import { calculateTco, Vehicle, EnergyParameters } from "../api/evClient";

export function TcoForm() {
  const [vehicle, setVehicle] = useState<Vehicle>();
  const [energy, setEnergy] = useState<EnergyParameters>();
  const [result, setResult] = useState<any>(null);

  useEffect(() => {
    fetch("http://localhost:8000/sample-payloads")
      .then((r) => r.json())
      .then((data) => {
        setVehicle(data.tco.vehicle);
        setEnergy(data.tco.energy_parameters);
      });
  }, []);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!vehicle || !energy) return;
    const response = await calculateTco({ vehicle, energy_parameters: energy });
    setResult(response);
  }

  return (
    <form onSubmit={onSubmit}>
      {/* form controls bound to vehicle/energy go here */}
      <button type="submit">Calculate TCO</button>
      {result && <pre>{JSON.stringify(result.summary, null, 2)}</pre>}
    </form>
  );
}
```
- Pair the form with charting (Recharts/Chart.js) and data-grid components for breakdowns.
- Mirror the tabs in `streamlit_app.py` as React routes (Configuration, Analysis) to keep UX parity.

## Running Streamlit alongside React
- Keep using `streamlit run streamlit_app.py` for Python-first analysis and validation.
- Use the same data definitions in both frontends so analysts can cross-check results: your React app consumes `/ev/*` endpoints, while Streamlit calls the underlying analyzers directly.

## Deployment tips
- Serve the React build via a CDN or reverse proxy and route API calls to the FastAPI backend.
- Enable auth/rate-limiting at the proxy if exposing the API publicly.
- Keep caching/memoization in the FastAPI layer for expensive runs (similar to `@st.cache_data` in Streamlit).
