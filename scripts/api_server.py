"""Standalone FastAPI application exposing the EV financial model.

Run with:
    uvicorn scripts.api_server:app --reload --port 8000
"""

from dataclasses import asdict
from typing import Any, Dict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ev_model.api import ev_router
from scripts.examples import (
    create_hybrid_vehicles,
    create_sample_energy_params,
    create_sample_evs,
    create_sample_financing,
    create_tax_incentives,
    create_traditional_vehicles,
)

if ev_router is None:  # pragma: no cover - requires optional FastAPI dependency
    raise ModuleNotFoundError(
        "FastAPI/Pydantic are required for the EV API. Install with 'pip install fastapi pydantic'."
    )

app = FastAPI(
    title="EV Financial Model API",
    version="1.0.0",
    description=(
        "Endpoints that wrap the Python EV financial model."
        " Use them from React or other clients for cost, comparison, and sensitivity analyses."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "*",  # enable quickly during local prototyping
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ev_router)


@app.get("/")
def root() -> Dict[str, Any]:
    """Health/info endpoint for quick smoke testing."""

    return {
        "status": "ok",
        "message": "EV Financial Model API is running. See /docs for OpenAPI schema.",
        "react_docs": "See docs/react_integration.md for wiring a React client.",
    }


def _build_sample_payloads() -> Dict[str, Any]:
    sample_evs = create_sample_evs()
    sample_energy = create_sample_energy_params()
    sample_financing = create_sample_financing()
    incentives = create_tax_incentives()
    traditional = create_traditional_vehicles()
    hybrids = create_hybrid_vehicles()

    default_vehicle = sample_evs["tesla_model_3"]
    default_energy = sample_energy["california"]

    return {
        "tco": {
            "vehicle": asdict(default_vehicle),
            "financing": asdict(sample_financing["standard_loan"]),
            "energy_parameters": asdict(default_energy),
            "tax_incentives": asdict(incentives["federal_and_state"]),
            "years": 10,
        },
        "comparison": {
            "ev_vehicle": asdict(default_vehicle),
            "ev_energy_params": asdict(default_energy),
            "traditional_vehicle": traditional["toyota_camry"],
            "hybrid_vehicle": hybrids["toyota_prius"],
            "years": 10,
            "annual_miles": 12_000,
        },
        "sensitivity": {
            "vehicle": asdict(default_vehicle),
            "energy_parameters": asdict(default_energy),
            "variable": "electricity_rate",
            "variation_percent": 10,
            "years": 10,
        },
    }


@app.get("/sample-payloads")
def sample_payloads() -> Dict[str, Any]:
    """Provide ready-made request bodies for the React client and testing."""

    payloads = _build_sample_payloads()

    # Keep the payloads at the top level so the React examples in the docs can
    # destructure `tco`, `comparison`, and `sensitivity` directly without
    # additional nesting.
    return {"status": "success", **payloads}


if __name__ == "__main__":  # pragma: no cover - manual execution helper
    import uvicorn

    uvicorn.run("scripts.api_server:app", host="0.0.0.0", port=8000, reload=True)
