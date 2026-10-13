# Digital Twin with EnergyPlus (DTWEP)

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](Licence.txt)
[![Python Version](https://img.shields.io/badge/Python-3.12%2B-blue.svg)](pyproject.toml)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688.svg)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/Frontend-React%2018%20%7C%20Vite%20%7C%20TypeScript-61dafb.svg)](https://react.dev)
[![Standard](https://img.shields.io/badge/Standard-ASHRAE%20Guideline%2014-success.svg)](https://www.ashrae.org)

**[English](README.md)** | **[Tiếng Việt](README_vi.md)**

---

## 📌 Overview

**Digital Twin with EnergyPlus (DTWEP)** is an open-source, extensible framework for building energy co-simulation, automated calibration, multi-scenario cross-validation, and physical degradation tracking. It bridges high-fidelity physics-based simulation engines (EnergyPlus / OpenStudio) with lightweight, fast-executing digital twin surrogate models optimized for edge computing and continuous operational monitoring.

DTWEP incorporates a pluggable **Multi-Case Platform** architecture. The benchmark implementation features an **Agrivoltaic Sawtooth Greenhouse** located in Ban Me Thuot, Vietnam, integrating microclimate dynamics, natural ventilation infiltration, roof-mounted photovoltaic (PV) generation, and Battery Energy Storage Systems (BESS).

### Core Problem & Concept
- **Model A (High-Fidelity Virtual World / Ground Truth)**: A multi-zone, geometrically detailed OpenStudio/EnergyPlus model capturing complex envelope shading, 3D solar distribution, and dynamic infiltration. While accurate, it is computationally intensive (~20–40s per simulation step), making it unsuitable for real-time edge control.
- **Model B (Simplified Digital Twin)**: A low-order, single-zone lumped thermal model designed for high-frequency co-simulation (~0.5–1.5s per step).
- **Genetic Algorithm (GA) Calibration Engine**: Automatically calibrates thermal, envelope, and electrical parameters of Model B against Model A target data to satisfy international calibration standards (**ASHRAE Guideline 14**).
- **Physical Degradation & Recalibration**: Simulates structural wear (e.g., membrane tearing causing increased air leakage) and PV efficiency degradation over time, automatically evaluating statistical drift and triggering adaptive recalibration.

---

## 🌟 Key Features

1. **Automated Calibration Engine**:
   - Multi-objective Genetic Algorithm (GA) with customizable population size, generations, mutation rate, and elitism.
   - Evaluates thermal, hygrometric, solar, and power flow variables simultaneously.
   - Publication-quality convergence plots and progress logging.

2. **ASHRAE Guideline 14 Compliance & Multi-Scale Metrics**:
   - Evaluates **Normalized Mean Bias Error (NMBE)** ($\le \pm 10\%$ hourly), **Coefficient of Variation of Root Mean Square Error (CVRMSE)** ($\le 30\%$ hourly), and **Coefficient of Determination ($R^2$)** ($\ge 0.70$).
   - Computes thermal metrics on the thermodynamic Kelvin scale ($T_K = T_C + 273.15$) to prevent zero-crossing distortion.
   - Supports additional statistical indicators: MAE, RMSE, and MAPE.

3. **Multi-Case Auto-Discovery Architecture**:
   - Decoupled core library (`calibration_framework/`) and domain cases (`cases/`).
   - Modular discovery via `case.yaml` specifications for models, experiments, and default configurations.

4. **Modular Simulation Adapters**:
   - Automated conversion between OpenStudio (`.osm`) and EnergyPlus (`.idf`).
   - Flexible Ground Truth providers: synthetic simulation, CSV time-series, field sensor measurements, and remote REST APIs.
   - Weather provider abstractions: EPW weather files, synthetic perturbations, and meteorological station streams.

5. **Full-Stack Web Interface & Real-Time Monitoring**:
   - **Backend**: FastAPI with asynchronous REST endpoints and WebSocket (`/ws/run`) for live terminal streaming and generation-by-generation GA fitness tracking.
   - **Frontend**: Modern Dark Glassmorphic Single-Page Application (SPA) built with React 18, Vite, TypeScript, Tailwind CSS, and Recharts.
   - **Dual Configuration Editor**: Visual slider/input forms alongside an integrated YAML editor with real-time syntax validation.
   - **Interactive Analytics**: Interactive co-simulation comparison charts, residual plots, ASHRAE compliance status badges, and a high-resolution plot gallery with lightbox viewer.

---

## 🏗️ Repository Structure

```
digital-twin-with-energy-plus/
├── app/                                 # Web application backend services
│   ├── case_manager.py                  # Case auto-discovery, configuration & result scanner
│   ├── experiment_runner.py             # Experiment process execution manager
│   └── module_runner.py                 # Asynchronous task runner & WebSocket logger
├── calibration_framework/               # Core calibration & co-simulation framework
│   ├── engine.py                        # Calibration execution engine
│   ├── evaluator.py                     # Loss function & multi-objective evaluator
│   ├── ground_truth.py                  # Ground truth providers (Simulation, CSV, API)
│   ├── metrics.py                       # Statistical metrics & ASHRAE Guideline 14 checker
│   ├── model_adapter.py                 # OpenStudio / EnergyPlus model translation & hooks
│   ├── plotting.py                      # Publication-grade plotting routines
│   ├── runner.py                        # EnergyPlus runner & SQLite output parser
│   ├── schemas.py                       # Pydantic schemas for configurations & data contracts
│   ├── timeseries.py                    # Time-series alignment and postprocessing utilities
│   ├── weather.py                       # EPW file parsers & synthetic weather generators
│   ├── experiments/                     # Abstract experiment benchmark base classes
│   │   ├── base.py                      # Experiment execution lifecycle base class
│   │   ├── exp1_initial_calibration.py  # Exp 1 core benchmark logic
│   │   ├── exp2_scenario_simulation.py  # Exp 2 core benchmark logic
│   │   └── exp3_recalibration.py        # Exp 3 core benchmark logic
│   └── optimizers/                      # Optimization algorithms
│       ├── base.py                      # Base optimizer interface
│       └── genetic_algorithm.py         # Genetic Algorithm (GA) implementation
├── cases/                               # Pluggable case studies directory
│   └── greenhouse/                      # Agrivoltaic Sawtooth Greenhouse case
│       ├── case.yaml                    # Case metadata, models, and registered experiments
│       ├── adapters.py                  # Domain-specific parameter mappers
│       ├── geometry.py                  # Parametric OpenStudio geometry generator
│       ├── model_transform.py           # Model A extension and simplification to Model B
│       ├── scenarios.py                 # Operational & meteorological scenario definitions
│       ├── exp1_initial_calibration.py  # Experiment 1 runner script
│       ├── exp2_scenario_simulation.py  # Experiment 2 runner script
│       ├── exp3_recalibration.py        # Experiment 3 runner script
│       └── configs/                     # YAML configuration files
│           ├── calibration.yaml         # GA search bounds, hyperparameters & weights
│           ├── exp1_initial_calibration.yaml
│           ├── exp2_scenario_simulation.yaml
│           └── exp3_recalibration.yaml
├── data/                                # Model files and weather datasets
│   ├── model_files/                     # Base and extended OSM / IDF models
│   └── weather/                         # EnergyPlus weather files (EPW)
├── frontend/                            # React + Vite + TypeScript frontend source code
│   ├── src/                             # UI components, API clients, and styles
│   ├── dist/                            # Production build served by FastAPI
│   └── package.json                     # Frontend dependencies & build scripts
├── results/                             # Generated experiment outputs, CSV metrics & plots
├── run_greenhouse_experiments.ps1       # Interactive PowerShell experiment runner (Windows)
├── run_greenhouse_experiments.sh        # Interactive Bash experiment runner (Linux/macOS)
├── main.py                              # FastAPI entry point (REST APIs, WebSocket, SPA host)
├── pyproject.toml                       # Python project configuration and dependencies
├── Licence.txt                          # GNU General Public License v3.0
└── README.md                            # Project documentation (English)
```

---

## 💻 System Requirements & Prerequisites

### Hardware
- **Processor**: Multi-core CPU (Intel Core i5/i7/i9 or AMD Ryzen 5/7/9, 4+ physical cores recommended for parallel simulation evaluation).
- **RAM**: Minimum 8 GB (16 GB recommended).
- **Disk Space**: At least 2 GB of free disk space for simulation run caches and generated SQLite databases.

### Software & Operating System
- **Operating System**: Windows 10/11, Ubuntu 20.04/22.04 LTS, or macOS 12+.
- **Python**: Version $\ge 3.12$.
- **Python Package Manager**: [uv](https://docs.astral.sh/uv/) (recommended for reproducible and fast environment management).
- **Node.js**: Version $\ge 18.0.0$ and npm (required for frontend compilation).
- **Building Energy Simulation Engines**:
  - `openstudio` ($\ge 3.8.0$)
  - `pyenergyplus-lbnl` ($\ge 24.0.0$ / managed automatically via `pyproject.toml`)

---

## 📦 Installation & Setup

### 1. Clone the Repository
```bash
git clone https://github.com/lehn85/digital-twin-with-energy-plus.git
cd digital-twin-with-energy-plus
```

### 2. Set Up Python Environment with `uv`
Install the virtual environment and all Python dependencies:
```bash
# Install uv if not already present (https://docs.astral.sh/uv/)
# Windows: powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
# Linux/macOS: curl -LsSf https://astral.sh/uv/install.sh | sh

uv sync
```

### 3. Build the Frontend SPA
Compile the React frontend into static assets in `frontend/dist/`:
```bash
cd frontend
npm install
npm run build
cd ..
```

---

## 🚀 Quick Start & Usage

### Option A: Interactive Web Dashboard (Recommended)

Start the unified FastAPI server:
```bash
uv run python main.py
```
Or run directly with Uvicorn:
```bash
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Once running:
- **Web User Interface**: Open [http://localhost:8000/](http://localhost:8000/) in your browser.
- **Interactive REST API Documentation (Swagger UI)**: [http://localhost:8000/docs](http://localhost:8000/docs).
- **Alternative API Documentation (ReDoc)**: [http://localhost:8000/redoc](http://localhost:8000/redoc).

#### Frontend Development Mode (Hot Reload)
To modify frontend code with instantaneous Hot Module Replacement (HMR):
```bash
cd frontend
npm run dev
```
Open [http://localhost:5173/](http://localhost:5173/). API and WebSocket calls are automatically proxied to the backend at `http://localhost:8000/`.

---

### Option B: Command-Line Experiment Runners

You can execute benchmark experiments via the built-in runner scripts.

#### Windows (PowerShell):
```powershell
# Interactive menu:
.\run_greenhouse_experiments.ps1

# Or run a specific experiment directly:
.\run_greenhouse_experiments.ps1 -Choice 1   # Experiment 1
.\run_greenhouse_experiments.ps1 -Choice 2   # Experiment 2
.\run_greenhouse_experiments.ps1 -Choice 3   # Experiment 3
.\run_greenhouse_experiments.ps1 -Choice 5   # Run all sequentially
```

#### Linux / macOS (Bash):
```bash
chmod +x run_greenhouse_experiments.sh

# Interactive menu:
./run_greenhouse_experiments.sh

# Or run directly:
./run_greenhouse_experiments.sh 1            # Experiment 1
./run_greenhouse_experiments.sh 2            # Experiment 2
./run_greenhouse_experiments.sh 3            # Experiment 3
./run_greenhouse_experiments.sh 5            # Run all sequentially
```

#### Direct Python Execution:
```bash
# Experiment 1: Initial Calibration Benchmark
uv run python cases/greenhouse/exp1_initial_calibration.py

# Experiment 2: Multi-Scenario Cross-Validation
uv run python cases/greenhouse/exp2_scenario_simulation.py

# Experiment 3: Physical Degradation Tracking Benchmark
uv run python cases/greenhouse/exp3_recalibration.py
```

---

## 🧪 Benchmark Experiments & Case Study

The platform includes three benchmark experiments for the Agrivoltaic Greenhouse:

| Experiment | Script | Configuration | Objective | Key Metrics |
| :--- | :--- | :--- | :--- | :--- |
| **Exp 1: Initial Calibration** | `cases/greenhouse/exp1_initial_calibration.py` | `exp1_initial_calibration.yaml` | Calibrate Model B against Model A baseline using Genetic Algorithm | NMBE, CVRMSE, $R^2$, Speedup ratio |
| **Exp 2: Multi-Scenario Validation** | `cases/greenhouse/exp2_scenario_simulation.py` | `exp2_scenario_simulation.yaml` | Cross-validate calibrated Model B across diverse operational scenarios | Multi-scenario NMBE, CVRMSE, Residual distribution |
| **Exp 3: Degradation Tracking** | `cases/greenhouse/exp3_recalibration.py` | `exp3_recalibration.yaml` | Detect physical wear (envelope leak + PV degradation) & trigger recalibration | Drift detection, Recalibration convergence |

### 1. Experiment 1: Initial Calibration Benchmark
- **Goal**: Tune Model B parameters (envelope thermal conductance, glazing SHGC, natural infiltration rates, ground conductivity, and PV efficiency) so that simulated outputs closely match Model A ground truth.
- **Output Artifacts**:
  - `results/greenhouse/exp1_initial_calibration/metrics.csv`: ASHRAE metrics for temperature, humidity, indoor solar, glass temperature, net grid, and PV generation.
  - `convergence_curve.png`: Fitness progression across GA generations.
  - `timeseries_comparison.png`: Hourly co-simulation comparison between Model A and Model B with residual errors.
  - `computational_performance.png`: Execution speedup comparison.

### 2. Experiment 2: Multi-Scenario Cross-Validation
- **Goal**: Evaluate the generalization fidelity of calibrated Model B across unobserved operating conditions without re-optimizing parameters.
- **Scenarios Evaluated**:
  - Baseline Standard Operation.
  - Extreme Heatwave (elevated dry-bulb temperatures and peak solar irradiance).
  - Heavy Precipitation & Cloud Cover.
  - High Natural Ventilation / Window Opening.
  - Peak Load Shifting (battery discharge scheduling).
- **Output Artifacts**:
  - `results/greenhouse/exp2_scenario_simulation/scenario_metrics.csv`
  - `scenario_comparison.png`

### 3. Experiment 3: Physical Degradation & Adaptive Recalibration
- **Goal**: Test the digital twin's capacity to maintain physical fidelity when unexpected physical faults occur:
  - *Envelope Infiltration Leak*: Simulating plastic film tearing (infiltration increased by $3\times$).
  - *PV Array Soiling/Degradation*: Simulating a $25\%$ reduction in PV power output.
- **Procedure**: The platform evaluates the uncalibrated error drift, triggers a secondary GA calibration round, and restores model compliance.
- **Output Artifacts**:
  - `results/greenhouse/exp3_recalibration/degradation_metrics.csv`
  - `recalibration_convergence.png`

---

## 📊 ASHRAE Guideline 14 Compliance Criteria

The system automatically validates time-series simulation outputs against the requirements of **ASHRAE Guideline 14-2014**:

$$\text{NMBE} = \frac{\sum_{i=1}^{n} (y_i - \hat{y}_i)}{(n - 1) \cdot \bar{y}} \times 100\%$$

$$\text{CVRMSE} = \frac{\sqrt{\frac{1}{n - 1} \sum_{i=1}^{n} (y_i - \hat{y}_i)^2}}{\bar{y}} \times 100\%$$

$$R^2 = 1 - \frac{\sum_{i=1}^{n} (y_i - \hat{y}_i)^2}{\sum_{i=1}^{n} (y_i - \bar{y})^2}$$

Where $y_i$ is the target value (Model A), $\hat{y}_i$ is the predicted value (Model B), $\bar{y}$ is the target mean, and $n$ is the total number of hourly observations.

| Metric | ASHRAE Guideline 14 Threshold (Hourly) | Target Pass Status |
| :--- | :--- | :--- |
| **NMBE** | $|\text{NMBE}| \le 10.0\%$ | Pass |
| **CVRMSE** | $\text{CVRMSE} \le 30.0\%$ | Pass |
| **$R^2$** | $R^2 \ge 0.70$ | Pass |

> **Note on Thermodynamic Variables**: For temperature variables, metrics are evaluated on the absolute thermodynamic Kelvin scale ($T_K = T_C + 273.15$) to prevent mathematical instability caused by zero-crossings or near-zero Celsius readings.

---

## ⚙️ Configuration & Customization

The platform uses structured YAML files to define parameters, GA constraints, and simulation parameters.

### Calibration Parameters (`cases/greenhouse/configs/calibration.yaml`)
```yaml
optimizer:
  type: "genetic_algorithm"
  population_size: 20
  generations: 15
  crossover_prob: 0.8
  mutation_prob: 0.2
  elite_count: 2

parameters:
  - name: "glazing_u_factor"
    target: "surface"
    min_value: 1.0
    max_value: 6.5
    default: 3.5
  - name: "infiltration_rate"
    target: "zone"
    min_value: 0.0001
    max_value: 0.0050
    default: 0.0015
  - name: "pv_efficiency"
    target: "generator"
    min_value: 0.10
    max_value: 0.24
    default: 0.18
```

### Adding a New Case Study
1. Create a new directory under `cases/<new_case_id>/`.
2. Define `case.yaml` specifying metadata, 3D models (`.osm` / `.idf`), and experiment list.
3. Provide domain adapters and configuration files in `cases/<new_case_id>/configs/`.
4. The system automatically detects the new case in the web dashboard upon restart.

---

## 📄 Output Artifacts & Reproducibility

All experiment runs save persistent artifacts under `results/<case_id>/<experiment_id>/`:
- `metrics.csv`: Complete numerical performance matrix for all target variables.
- `convergence.json`: Per-generation best and mean fitness scores.
- `best_parameters.yaml`: Calibrated parameter values discovered by the GA.
- `plots/`: High-resolution figures (`.png`, 300 DPI) ready for research reporting:
  - `convergence_curve.png`
  - `timeseries_comparison.png`
  - `scenario_comparison.png`
  - `recalibration_comparison.png`

---

## 📜 License

This project is licensed under the **GNU General Public License v3.0 (GPLv3)**. See the [Licence.txt](Licence.txt) file for the complete license text.

---

## ✉️ Contact & Support

For questions, issues, or contributions:
- **Repository**: [https://github.com/lehn85/digital-twin-with-energy-plus](https://github.com/lehn85/digital-twin-with-energy-plus)
- **Author**: lehn85 (`lehn85@gmail.com`)
