from __future__ import annotations
import os
import sys
import asyncio
import json
from pathlib import Path
from typing import Any, Dict, Optional
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

# Ensure workspace root is in sys.path
WORKSPACE_ROOT = Path(__file__).resolve().parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from app.case_manager import CaseManager
from app.module_runner import global_runner
from calibration_framework import translate_osm_to_idf
from cases.greenhouse import (
    extend_greenhouse_osm,
    simplify_to_model_b,
)

app = FastAPI(
    title="Digital Twin with EnergyPlus (DTWEP) API",
    description="Multi-case Digital Twin Building & Greenhouse Energy Calibration Platform with EnergyPlus",
    version="0.3.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

case_manager = CaseManager(WORKSPACE_ROOT)

# Pre-computation / model preparation
MODELS_DIR = WORKSPACE_ROOT / "cases" / "greenhouse" / "models"
RESULTS_MODELS_DIR = WORKSPACE_ROOT / "results" / "greenhouse" / "models"
BASE_OSM_A = MODELS_DIR / "greenhouse_sawtooth.osm"
EXTENDED_OSM_A = RESULTS_MODELS_DIR / "greenhouse_sawtooth_extended.osm"
EXTENDED_IDF_A = RESULTS_MODELS_DIR / "greenhouse_sawtooth_extended.idf"

BASE_OSM_B = RESULTS_MODELS_DIR / "greenhouse_simple.osm"
EXTENDED_OSM_B = RESULTS_MODELS_DIR / "greenhouse_simple_extended.osm"
EXTENDED_IDF_B = RESULTS_MODELS_DIR / "greenhouse_simple_extended.idf"


@app.on_event("startup")
def startup_event():
    print("Startup: Checking and preparing Greenhouse baseline models...")
    RESULTS_MODELS_DIR.mkdir(parents=True, exist_ok=True)
    try:
        if BASE_OSM_A.exists() and (not EXTENDED_IDF_A.exists() or not EXTENDED_IDF_B.exists()):
            simplify_to_model_b(str(BASE_OSM_A), str(BASE_OSM_B))
            extend_greenhouse_osm(str(BASE_OSM_A), str(EXTENDED_OSM_A))
            extend_greenhouse_osm(str(BASE_OSM_B), str(EXTENDED_OSM_B))
            translate_osm_to_idf(str(EXTENDED_OSM_A), str(EXTENDED_IDF_A))
            translate_osm_to_idf(str(EXTENDED_OSM_B), str(EXTENDED_IDF_B))
            print("Extended IDFs ready in results/greenhouse/models.")
    except Exception as e:
        print(f"Startup model preparation notice: {e}")


# -----------------------------------------------------------------------------
# REST API Endpoints
# -----------------------------------------------------------------------------

@app.get("/api/cases")
def list_cases():
    """Returns a list of all auto-discovered digital twin cases."""
    return {"cases": case_manager.list_cases()}


@app.get("/api/cases/{case_id}")
def get_case(case_id: str):
    """Returns full details, modules list, and model status for a specific case."""
    detail = case_manager.get_case_detail(case_id)
    if not detail:
        raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found.")
    return detail


@app.get("/api/cases/{case_id}/modules/{mod_id}")
@app.get("/api/cases/{case_id}/experiments/{mod_id}")
def get_module(case_id: str, mod_id: str):
    """Returns details, configuration, and result summary for a specific module."""
    detail = case_manager.get_case_detail(case_id)
    if not detail:
        raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found.")

    modules = detail.get("modules", detail.get("experiments", []))
    mod = next((m for m in modules if m["id"] == mod_id), None)
    if not mod:
        raise HTTPException(status_code=404, detail=f"Module '{mod_id}' not found in case '{case_id}'.")

    # If module has config_file, attach config details
    config_info = None
    if mod.get("config_file"):
        config_info = case_manager.get_config(case_id, mod["config_file"])

    results = case_manager.get_results(case_id, mod_id)

    return {
        "module": mod,
        "experiment": mod,
        "config": config_info,
        "results": results,
    }


@app.get("/api/cases/{case_id}/configs/{config_name}")
def get_config(case_id: str, config_name: str):
    """Fetches raw YAML and parsed content of a configuration file."""
    cfg = case_manager.get_config(case_id, config_name)
    if not cfg:
        raise HTTPException(status_code=404, detail=f"Config '{config_name}' not found.")
    return cfg


class SaveConfigRequest(BaseModel):
    yaml_content: str


@app.put("/api/cases/{case_id}/configs/{config_name}")
def save_config(case_id: str, config_name: str, payload: SaveConfigRequest):
    """Validates and updates a YAML configuration file."""
    res = case_manager.save_config(case_id, config_name, payload.yaml_content)
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error", "Failed to save configuration."))
    return res


@app.get("/api/cases/{case_id}/results/{mod_id}")
def get_results(case_id: str, mod_id: str):
    """Fetches metrics, scenario comparison, and plot lists for a module."""
    return case_manager.get_results(case_id, mod_id)


@app.get("/api/cases/{case_id}/plots/{mod_id}/{plot_name}")
def get_plot(case_id: str, mod_id: str, plot_name: str):
    """Serves high-resolution plot PNG images generated by modules."""
    plot_path = case_manager.get_plot_path(case_id, mod_id, plot_name)
    if not plot_path:
        raise HTTPException(status_code=404, detail="Plot file not found.")
    return FileResponse(plot_path, media_type="image/png")


@app.post("/api/cases/{case_id}/stop")
def stop_running_processes(case_id: str):
    """Cancels any running module or calibration subprocesses."""
    global_runner.cancel_all()
    return {"success": True, "message": "All running processes stopped."}


# -----------------------------------------------------------------------------
# WebSocket Real-Time Execution Manager
# -----------------------------------------------------------------------------

@app.websocket("/ws/run")
async def websocket_run(websocket: WebSocket):
    """
    Universal WebSocket endpoint for live module execution, log streaming,
    and interactive GA calibration with progress tracking.
    """
    await websocket.accept()
    loop = asyncio.get_running_loop()

    try:
        while True:
            raw = await websocket.receive_text()
            msg = json.loads(raw)
            action = msg.get("action")

            if action in ("start_module", "start_experiment"):
                case_id = msg.get("case_id", "greenhouse")
                mod_id = msg.get("mod_id") or msg.get("exp_id")
                force_model_a = msg.get("force_model_a", False)

                case_detail = case_manager.get_case_detail(case_id)
                if not case_detail:
                    await websocket.send_json({"type": "error", "message": f"Case '{case_id}' not found."})
                    continue

                modules = case_detail.get("modules", case_detail.get("experiments", []))
                mod = next((m for m in modules if m["id"] == mod_id), None)
                if not mod or not mod.get("script"):
                    await websocket.send_json({"type": "error", "message": f"Module script not found for '{mod_id}'."})
                    continue

                script_path = mod["script"]
                config_path = f"cases/{case_id}/configs/{mod['config_file']}" if mod.get("config_file") else None

                await websocket.send_json({
                    "type": "status",
                    "status": "RUNNING",
                    "message": f"Starting {mod.get('name', mod_id)}...",
                })

                def on_log(line: str, stream: str):
                    asyncio.run_coroutine_threadsafe(
                        websocket.send_json({
                            "type": "log",
                            "stream": stream,
                            "line": line,
                        }),
                        loop,
                    )

                exit_code = await global_runner.run_module_process(
                    script_path=script_path,
                    config_path=config_path,
                    force_model_a=force_model_a,
                    on_log=on_log,
                )

                # Fetch updated results
                results = case_manager.get_results(case_id, mod_id)

                await websocket.send_json({
                    "type": "finished",
                    "exit_code": exit_code,
                    "success": exit_code == 0,
                    "message": f"Module completed with exit code {exit_code}." if exit_code == 0 else f"Module failed (exit code {exit_code}).",
                    "results": results,
                })

    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"WebSocket execution error: {e}")


# -----------------------------------------------------------------------------
# Frontend Static Asset Serving
# -----------------------------------------------------------------------------

FRONTEND_DIST = WORKSPACE_ROOT / "frontend" / "dist"
if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}")
    def serve_frontend_spa(full_path: str):
        file_target = FRONTEND_DIST / full_path
        if file_target.exists() and file_target.is_file():
            return FileResponse(file_target)
        index_html = FRONTEND_DIST / "index.html"
        if index_html.exists():
            return FileResponse(index_html)
        return HTMLResponse("<h1>Frontend is building...</h1>")
else:
    @app.get("/")
    def serve_fallback():
        return {
            "message": "DTWEP API Server is Running.",
            "frontend": "Frontend dev server running on Vite port (default :5173). Build frontend for static production hosting.",
            "docs": "/docs",
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
