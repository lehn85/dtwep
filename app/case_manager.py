from __future__ import annotations
import os
import glob
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml
import pandas as pd

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent


class CaseManager:
    """
    Central service for discovering and managing Digital Twin cases,
    their configurations, modules, and simulation/calibration results.
    """

    def __init__(self, root_dir: Optional[Path] = None):
        self.root_dir = root_dir or WORKSPACE_ROOT
        self.cases_dir = self.root_dir / "cases"
        self.results_dir = self.root_dir / "results"
        self.data_dir = self.root_dir / "data"

    def list_cases(self) -> List[Dict[str, Any]]:
        """
        Discovers and lists all cases available in the `cases/` directory.
        """
        cases = []
        if not self.cases_dir.exists():
            return cases

        for item in sorted(self.cases_dir.iterdir()):
            if item.is_dir() and not item.name.startswith((".", "_")):
                case_info = self.get_case_summary(item.name)
                if case_info:
                    cases.append(case_info)

        return cases

    def get_case_summary(self, case_id: str) -> Optional[Dict[str, Any]]:
        """
        Gets summary metadata for a specific case.
        """
        case_path = self.cases_dir / case_id
        if not case_path.exists() or not case_path.is_dir():
            return None

        manifest_file = case_path / "case.yaml"
        if manifest_file.exists():
            try:
                with open(manifest_file, "r", encoding="utf-8") as f:
                    manifest = yaml.safe_load(f) or {}
                manifest["id"] = case_id
                manifest["type"] = manifest.get("type", "virtual")
                manifest["has_manifest"] = True
                
                # Normalize modules / experiments
                if "modules" in manifest:
                    manifest["modules"] = manifest["modules"]
                elif "experiments" in manifest:
                    manifest["modules"] = manifest["experiments"]
                else:
                    manifest["modules"] = []
                manifest["experiments"] = manifest["modules"]
                return manifest
            except Exception as e:
                print(f"Error loading case.yaml for {case_id}: {e}")

        # Fallback: Auto-generate metadata from filesystem inspection
        title = case_id.replace("_", " ").title()
        configs = []
        configs_dir = case_path / "configs"
        if configs_dir.exists():
            configs = [f.name for f in configs_dir.glob("*.yaml")]

        modules = []
        scripts = sorted(list(case_path.glob("mod*.py")) + list(case_path.glob("exp*.py")))
        for script in scripts:
            mod_id = script.stem
            mod_name = mod_id.replace("_", " ").title()
            cfg_name = f"{mod_id}.yaml"
            modules.append({
                "id": mod_id,
                "name": mod_name,
                "description": f"Module script {script.name}",
                "config_file": cfg_name if (configs_dir / cfg_name).exists() else None,
                "script": str(script.relative_to(self.root_dir)),
                "results_dir": f"results/{case_id}/{mod_id}",
            })

        return {
            "id": case_id,
            "name": title,
            "type": "virtual",
            "description": f"Digital Twin Case for {title}",
            "category": "Building Energy",
            "icon": "Building",
            "tags": [case_id],
            "has_manifest": False,
            "modules": modules,
            "experiments": modules,
            "configs": configs,
        }

    def get_case_detail(self, case_id: str) -> Optional[Dict[str, Any]]:
        """
        Gets full details for a case including model files existence and modules list.
        """
        summary = self.get_case_summary(case_id)
        if not summary:
            return None

        case_path = self.cases_dir / case_id
        configs_dir = case_path / "configs"
        available_configs = []
        if configs_dir.exists():
            for cf in sorted(configs_dir.glob("*.yaml")):
                available_configs.append(cf.name)

        summary["available_configs"] = available_configs

        # Inspect modules and check result availability
        modules = summary.get("modules", summary.get("experiments", []))
        enriched_modules = []
        for mod in modules:
            mod_copy = dict(mod)
            mod_res_dir = self.root_dir / mod_copy.get("results_dir", f"results/{case_id}/{mod_copy['id']}")
            mod_copy["has_results"] = mod_res_dir.exists()
            
            # Check metrics file
            metrics_file = mod_res_dir / "accuracy_metrics.csv"
            if not metrics_file.exists():
                metrics_file = mod_res_dir / "scenarios_metrics_summary.csv"
            if not metrics_file.exists():
                metrics_file = mod_res_dir / "recalibration_metrics.csv"
            if not metrics_file.exists():
                metrics_file = mod_res_dir / "metrics.csv"
            mod_copy["has_metrics"] = metrics_file.exists()
            
            # Check plot images (both directly in res_dir and in res_dir/plots)
            plot_files = []
            if mod_res_dir.exists():
                plot_files.extend([p.name for p in mod_res_dir.glob("*.png")])
            plots_dir = mod_res_dir / "plots"
            if plots_dir.exists():
                plot_files.extend([p.name for p in plots_dir.glob("*.png")])
            plot_files = sorted(list(set(plot_files)))
            mod_copy["plot_count"] = len(plot_files)
            mod_copy["plots"] = plot_files

            enriched_modules.append(mod_copy)

        summary["modules"] = enriched_modules
        summary["experiments"] = enriched_modules

        # Verify model files
        models = summary.get("models", {})
        model_status = {}
        for m_key, m_info in models.items():
            if isinstance(m_info, dict):
                m_status = {}
                for k, p_val in m_info.items():
                    if isinstance(p_val, str) and (
                        any(k.endswith(sfx) for sfx in ["_osm", "_idf", "_fmu", "_mo", "_path", "_file", "_model"])
                        or any(p_val.lower().endswith(ext) for ext in [".osm", ".idf", ".fmu", ".mo", ".py", ".onnx", ".pkl", ".mat", ".json", ".csv", ".yaml", ".xml", ".epw"])
                    ):
                        m_status[k] = {
                            "path": p_val,
                            "exists": (self.root_dir / p_val).exists(),
                        }
                model_status[m_key] = m_status
        summary["model_status"] = model_status

        return summary

    def get_config(self, case_id: str, config_name: str) -> Optional[Dict[str, Any]]:
        """
        Reads and returns YAML configuration file content (raw text + parsed dictionary).
        """
        cfg_path = self.cases_dir / case_id / "configs" / config_name
        if not cfg_path.exists():
            return None

        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                raw_text = f.read()
            parsed = yaml.safe_load(raw_text) or {}
            return {
                "case_id": case_id,
                "config_name": config_name,
                "file_path": str(cfg_path.relative_to(self.root_dir)),
                "raw_yaml": raw_text,
                "parsed": parsed,
            }
        except Exception as e:
            return {
                "case_id": case_id,
                "config_name": config_name,
                "error": str(e),
            }

    def save_config(self, case_id: str, config_name: str, yaml_content: str) -> Dict[str, Any]:
        """
        Validates and saves YAML configuration.
        """
        try:
            parsed = yaml.safe_load(yaml_content)
            if not isinstance(parsed, dict):
                return {"success": False, "error": "YAML content must evaluate to a dictionary/mapping."}
        except Exception as e:
            return {"success": False, "error": f"Invalid YAML syntax: {e}"}

        cfg_dir = self.cases_dir / case_id / "configs"
        cfg_dir.mkdir(parents=True, exist_ok=True)
        cfg_path = cfg_dir / config_name

        try:
            with open(cfg_path, "w", encoding="utf-8") as f:
                f.write(yaml_content)
            return {"success": True, "message": f"Successfully saved {config_name}", "parsed": parsed}
        except Exception as e:
            return {"success": False, "error": f"Failed to write file: {e}"}

    def get_results(self, case_id: str, mod_id: str) -> Dict[str, Any]:
        """
        Retrieves metrics, plots, and time-series data for a given module.
        Dynamically reads case & module configuration to enrich metadata.
        """
        case_detail = self.get_case_detail(case_id)
        if not case_detail:
            return {"error": f"Case '{case_id}' not found."}

        modules = case_detail.get("modules", case_detail.get("experiments", []))
        mod_info = next((m for m in modules if m["id"] == mod_id), None)
        res_dir_rel = mod_info.get("results_dir", f"results/{case_id}/{mod_id}") if mod_info else f"results/{case_id}/{mod_id}"
        res_dir = self.root_dir / res_dir_rel

        # Load module config if available
        mod_config: Dict[str, Any] = {}
        if mod_info and mod_info.get("config_file"):
            cfg_data = self.get_config(case_id, mod_info["config_file"])
            if cfg_data and "parsed" in cfg_data and isinstance(cfg_data["parsed"], dict):
                mod_config = cfg_data["parsed"]
        elif (self.cases_dir / case_id / "configs" / f"{mod_id}.yaml").exists():
            cfg_data = self.get_config(case_id, f"{mod_id}.yaml")
            if cfg_data and "parsed" in cfg_data and isinstance(cfg_data["parsed"], dict):
                mod_config = cfg_data["parsed"]

        # Parse variable metadata (y_labels & units) from module config
        variable_meta: Dict[str, Dict[str, str]] = {}
        y_labels = mod_config.get("y_labels", {})
        if isinstance(y_labels, dict):
            for var_key, label_str in y_labels.items():
                label_val = str(label_str)
                unit_val = ""
                clean_label = label_val
                if "(" in label_val and label_val.endswith(")"):
                    parts = label_val.rsplit("(", 1)
                    clean_label = parts[0].strip()
                    unit_val = parts[1][:-1].strip()
                variable_meta[str(var_key)] = {
                    "label": clean_label,
                    "unit": unit_val,
                    "full_label": label_val,
                }

        target_vars = mod_config.get("target_variables")
        if isinstance(target_vars, list):
            target_vars = [str(v) for v in target_vars]
        else:
            target_vars = None

        # Parse outputs config from module config if present
        outputs_cfg = mod_config.get("outputs")

        if not res_dir.exists():
            return {
                "case_id": case_id,
                "mod_id": mod_id,
                "exp_id": mod_id,
                "has_results": False,
                "message": "No results generated yet. Run the module to view metrics and plots.",
                "exp_config": mod_config,
                "mod_config": mod_config,
                "outputs": outputs_cfg,
                "variable_meta": variable_meta,
                "models": case_detail.get("models"),
            }

        data: Dict[str, Any] = {
            "case_id": case_id,
            "mod_id": mod_id,
            "exp_id": mod_id,
            "has_results": True,
            "results_dir": str(res_dir_rel),
            "metrics": [],
            "scenarios_metrics": [],
            "plots": [],
            "timeseries_preview": [],
            "exp_config": mod_config,
            "mod_config": mod_config,
            "outputs": outputs_cfg,
            "variable_meta": variable_meta,
            "models": case_detail.get("models"),
            "case_name": case_detail.get("name"),
            "mod_name": mod_info.get("name") if mod_info else mod_id,
            "exp_name": mod_info.get("name") if mod_info else mod_id,
        }

        # 1. Parse metrics (accuracy_metrics.csv, recalibration_metrics.csv, metrics.csv)
        for m_cand in [
            res_dir / "accuracy_metrics.csv",
            res_dir / "recalibration_metrics.csv",
            res_dir / "metrics.csv",
        ]:
            if m_cand.exists():
                try:
                    df = pd.read_csv(m_cand)
                    df = df.fillna(0).replace([float("inf"), float("-inf")], 0)
                    data["metrics"] = df.to_dict(orient="records")
                    break
                except Exception as e:
                    print(f"Error reading {m_cand}: {e}")

        # 2. Parse scenarios_metrics_summary.csv or all_scenarios_metrics.csv
        for sc_cand in [
            res_dir / "scenarios_metrics_summary.csv",
            res_dir / "all_scenarios_metrics.csv",
        ]:
            if sc_cand.exists():
                try:
                    df_sc = pd.read_csv(sc_cand)
                    df_sc = df_sc.fillna(0).replace([float("inf"), float("-inf")], 0)
                    data["scenarios_metrics"] = df_sc.to_dict(orient="records")
                    break
                except Exception as e:
                    print(f"Error reading {sc_cand}: {e}")

        # 3. List plot images
        plot_paths: List[Path] = []
        plot_paths.extend(sorted(res_dir.glob("*.png")))
        plots_dir = res_dir / "plots"
        if plots_dir.exists():
            plot_paths.extend(sorted(plots_dir.glob("*.png")))

        seen_names = set()
        for p in plot_paths:
            if p.name not in seen_names:
                seen_names.add(p.name)
                data["plots"].append({
                    "name": p.name,
                    "title": p.stem.replace("_", " ").title(),
                    "url": f"/api/cases/{case_id}/plots/{mod_id}/{p.name}",
                    "size_bytes": p.stat().st_size,
                })

        # 4. Extract calibration history
        data["calibration_history"] = self._extract_calibration_history(res_dir)

        # 5. Extract simulation execution times & performance speedup
        data["performance"] = self._extract_performance(res_dir)

        # 6. Extract synchronized time-series data
        data["timeseries"] = self._extract_timeseries_data(
            res_dir,
            target_vars=target_vars,
            variable_meta=variable_meta
        )

        return data

    def _extract_performance(self, res_dir: Path) -> Optional[Dict[str, Any]]:
        """
        Extracts simulation execution time comparison between Model A and Model B and computes speedup.
        """
        perf_csv = res_dir / "computational_performance.csv"
        if perf_csv.exists():
            try:
                df = pd.read_csv(perf_csv)
                row_a = df[df["Model"].str.contains("Model A|Ground Truth|Target|HFM", case=False)]
                row_b = df[df["Model"].str.contains("Model B|Digital Twin|Calibrated|ROM|Surrogate", case=False)]
                if row_a.empty and len(df) >= 2:
                    row_a = df.iloc[[0]]
                    row_b = df.iloc[[1]]
                if not row_a.empty and not row_b.empty:
                    time_a = float(row_a["Execution_Time_s"].values[0])
                    time_b = float(row_b["Execution_Time_s"].values[0])
                    speedup = round(time_a / max(time_b, 1e-3), 1)
                    return {
                        "time_a": round(time_a, 2),
                        "time_b": round(time_b, 2),
                        "speedup": speedup,
                        "unit": "s",
                    }
            except Exception:
                pass

        time_a_file = res_dir / "model_a_sim_time.txt"
        time_a: Optional[float] = None
        if time_a_file.exists():
            try:
                time_a = float(time_a_file.read_text().strip())
            except Exception:
                pass

        time_b: Optional[float] = None
        cal_history = self._extract_calibration_history(res_dir)
        if cal_history:
            exec_times = [
                item["mean_exec_time_s"]
                for item in cal_history
                if "mean_exec_time_s" in item and item["mean_exec_time_s"] > 0
            ]
            if exec_times:
                time_b = sum(exec_times) / len(exec_times)

        if time_a is not None and time_b is not None and time_b > 0:
            speedup = round(time_a / max(time_b, 1e-3), 1)
            return {
                "time_a": round(time_a, 2),
                "time_b": round(time_b, 2),
                "speedup": speedup,
                "unit": "s",
            }
        return None

    def _extract_calibration_history(self, res_dir: Path) -> List[Dict[str, Any]]:
        """
        Attempts to read GA calibration history / convergence curve from result directory.
        """
        cal_history: List[Dict[str, Any]] = []
        cal_candidates = [
            res_dir / "calibration_history.csv",
            res_dir / "fitness_history.csv",
            res_dir / "ga_results.csv",
        ]
        cal_files = [c for c in cal_candidates if c.exists()]
        if not cal_files:
            cal_files = list(res_dir.glob("**/calibration_history.csv")) + list(res_dir.glob("**/ga_results.csv"))

        if not cal_files:
            return cal_history

        try:
            df = pd.read_csv(cal_files[0])
            df = df.fillna(0).replace([float("inf"), float("-inf")], 0)
            for idx, row in df.iterrows():
                gen_val = int(row.get("generation", row.get("iteration", idx + 1)))
                item = {
                    "generation": gen_val,
                    "best_fitness": round(float(row.get("best_fitness", 0)), 5),
                }
                if "mean_fitness" in row:
                    item["mean_fitness"] = round(float(row["mean_fitness"]), 5)
                if "diversity" in row:
                    item["diversity"] = round(float(row["diversity"]), 5)
                if "mean_exec_time_s" in row:
                    item["mean_exec_time_s"] = round(float(row["mean_exec_time_s"]), 2)
                cal_history.append(item)
        except Exception as e:
            print(f"Error extracting calibration history from {res_dir}: {e}")

        return cal_history

    def _extract_timeseries_data(
        self,
        res_dir: Path,
        target_vars: Optional[List[str]] = None,
        variable_meta: Optional[Dict[str, Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """
        Extracts synchronized time-series data comparing Model A vs Model B across scenarios.
        """
        timeseries: Dict[str, Any] = {
            "available": False,
            "points": [],
            "variables": [],
            "variable_meta": variable_meta or {},
            "scenarios": {},
            "selected_scenario": "",
        }

        def format_time_label(step_idx: int, interval_mins: int = 10) -> str:
            total_mins = max(0, step_idx - 1) * interval_mins
            day = (total_mins // 1440) + 1
            rem_mins = total_mins % 1440
            hours = rem_mins // 60
            mins = rem_mins % 60
            return f"D{day} {hours:02d}:{mins:02d}"

        def discover_variables(df_a: pd.DataFrame, df_b: pd.DataFrame) -> List[str]:
            ignore_cols = {
                "timeindex", "step", "time", "date/time", "datetime",
                "timestamp", "hour", "day", "minute", "index", "unnamed: 0",
                "scenario", "scenario_name",
            }
            all_cols_a = set(df_a.columns)
            all_cols_b = set(df_b.columns)
            shared_cols = [
                c for c in df_a.columns
                if c in all_cols_b and c.lower() not in ignore_cols and pd.api.types.is_numeric_dtype(df_a[c])
            ]
            
            if target_vars:
                ordered_vars = [v for v in target_vars if v in shared_cols or (v in all_cols_a and v in all_cols_b)]
                for c in shared_cols:
                    if c not in ordered_vars and c.lower() not in ignore_cols:
                        ordered_vars.append(c)
                return ordered_vars
            return shared_cols

        def process_pair(df_a: pd.DataFrame, df_b: pd.DataFrame):
            present_vars = discover_variables(df_a, df_b)
            n_points = min(len(df_a), len(df_b))
            points_list = []
            for i in range(n_points):
                row_a = df_a.iloc[i]
                row_b = df_b.iloc[i]
                time_idx = int(row_a.get("TimeIndex", i + 1)) if "TimeIndex" in row_a else i + 1
                
                # Check for existing descriptive time column or generate formatted label
                if "time" in row_a and isinstance(row_a["time"], str) and row_a["time"].strip():
                    time_val = str(row_a["time"])
                elif "datetime" in row_a and isinstance(row_a["datetime"], str) and row_a["datetime"].strip():
                    time_val = str(row_a["datetime"])
                elif "Date/Time" in row_a and isinstance(row_a["Date/Time"], str) and row_a["Date/Time"].strip():
                    time_val = str(row_a["Date/Time"])
                else:
                    time_val = format_time_label(time_idx)

                pt: Dict[str, Any] = {
                    "step": time_idx,
                    "time": time_val,
                }
                for v in present_vars:
                    if v in row_a and not pd.isna(row_a[v]):
                        pt[f"{v}_a"] = round(float(row_a[v]), 3)
                    if v in row_b and not pd.isna(row_b[v]):
                        pt[f"{v}_b"] = round(float(row_b[v]), 3)
                points_list.append(pt)

            return points_list, present_vars

        try:
            # Case 1: Multi-scenario module (e.g. Exp 2)
            known_single_dirs = {
                "target_run", "calibrated_b_run", "baseline_b_run", "recalibration_run",
                "model_b_pre_recalibration", "target_perturbed_run", "model_a", "model_b",
                ".weather_cache", "plots"
            }
            scenario_dirs = sorted([
                d for d in res_dir.iterdir()
                if d.is_dir() and d.name not in known_single_dirs and (
                    (d / "timeseries.csv").exists()
                    or (d / "target_run").exists()
                    or (d / "model_b_run").exists()
                    or (d / "simulation_results.csv").exists()
                    or (d / "model_a_results.csv").exists()
                )
            ])
            if scenario_dirs:
                scenarios_dict: Dict[str, Any] = {}
                default_scenario_name = ""
                for sc_dir in scenario_dirs:
                    sc_name = sc_dir.name
                    if not default_scenario_name:
                        default_scenario_name = sc_name

                    sc_ts_file = sc_dir / "timeseries.csv"
                    if sc_ts_file.exists():
                        df_sc_ts = pd.read_csv(sc_ts_file)
                        df_sc_ts = df_sc_ts.fillna(0).replace([float("inf"), float("-inf")], 0)
                        pts = df_sc_ts.to_dict(orient="records")
                        vars_list = [c[:-2] for c in df_sc_ts.columns if c.endswith("_a")]
                        if not vars_list:
                            vars_list = [c[:-2] for c in df_sc_ts.columns if c.endswith("_b")]
                        if not vars_list:
                            vars_list = [c for c in df_sc_ts.columns if c.lower() not in {"step", "time", "timeindex", "index", "date/time", "datetime"}]
                    else:
                        # Find Model A CSV in scenario dir
                        sc_df_a_path = None
                        for cand in [
                            sc_dir / "target_run" / "target_results.csv",
                            sc_dir / "target_run" / "simulation_results.csv",
                            sc_dir / "target_run" / "sim_results.csv",
                            sc_dir / "model_a_results.csv",
                            sc_dir / "target_results.csv",
                        ]:
                            if cand.exists():
                                sc_df_a_path = cand
                                break

                        # Find Model B CSV in scenario dir
                        sc_df_b_path = None
                        for cand in [
                            sc_dir / "model_b_run" / "simulation_results.csv",
                            sc_dir / "model_b_run" / "sim_results.csv",
                            sc_dir / "model_b_run" / "calibrated_simulation_results.csv",
                            sc_dir / "model_b_results.csv",
                            sc_dir / "simulation_results.csv",
                        ]:
                            if cand.exists():
                                sc_df_b_path = cand
                                break

                        if sc_df_a_path and sc_df_b_path:
                            df_a = pd.read_csv(sc_df_a_path)
                            df_b = pd.read_csv(sc_df_b_path)
                            pts, vars_list = process_pair(df_a, df_b)
                        else:
                            continue

                    scenarios_dict[sc_name] = {
                        "name": sc_name,
                        "title": sc_name.replace("_", " ").title(),
                        "points": pts,
                        "variables": vars_list,
                    }

                if scenarios_dict:
                    timeseries["available"] = True
                    timeseries["scenarios"] = scenarios_dict
                    timeseries["selected_scenario"] = default_scenario_name
                    timeseries["points"] = scenarios_dict[default_scenario_name]["points"]
                    timeseries["variables"] = scenarios_dict[default_scenario_name]["variables"]
                    return timeseries

            # Case 2: Pre-exported timeseries.csv at root of results_dir
            root_ts_file = res_dir / "timeseries.csv"
            if root_ts_file.exists():
                df_ts = pd.read_csv(root_ts_file)
                df_ts = df_ts.fillna(0).replace([float("inf"), float("-inf")], 0)
                pts = df_ts.to_dict(orient="records")
                vars_list = [c[:-2] for c in df_ts.columns if c.endswith("_a")]
                if not vars_list:
                    vars_list = [c[:-2] for c in df_ts.columns if c.endswith("_b")]
                if not vars_list:
                    vars_list = [c for c in df_ts.columns if c.lower() not in {"step", "time", "timeindex", "index", "date/time", "datetime"}]
                if target_vars:
                    vars_list = [v for v in target_vars if v in vars_list] + [v for v in vars_list if v not in target_vars]
                timeseries["available"] = True
                timeseries["points"] = pts
                timeseries["variables"] = vars_list
                return timeseries

            # Case 3: Inspection for target and calibrated runs (Exp 1, Exp 3, etc.)
            model_a_csv: Optional[Path] = None
            for cand in [
                res_dir / "target_run" / "target_results.csv",
                res_dir / "target_perturbed_run" / "target_results.csv",
                res_dir / "target_run" / "simulation_results.csv",
                res_dir / "target_perturbed_run" / "simulation_results.csv",
                res_dir / "target_run" / "sim_results.csv",
                res_dir / "target_perturbed_run" / "sim_results.csv",
                res_dir / "model_a" / "target_results.csv",
                res_dir / "model_a_results.csv",
                res_dir / "target_results.csv",
            ]:
                if cand.exists():
                    model_a_csv = cand
                    break

            model_b_csv: Optional[Path] = None
            for cand in [
                res_dir / "calibrated_b_run" / "calibrated_simulation_results.csv",
                res_dir / "calibrated_b_run" / "simulation_results.csv",
                res_dir / "calibrated_b_run" / "sim_results.csv",
                res_dir / "recalibration_run" / "recalibrated_simulation_results.csv",
                res_dir / "recalibration_run" / "simulation_results.csv",
                res_dir / "recalibration_run" / "sim_results.csv",
                res_dir / "model_b_run" / "simulation_results.csv",
                res_dir / "model_b_run" / "sim_results.csv",
                res_dir / "model_b_post_recalibration" / "sim_results.csv",
                res_dir / "model_b_post_recalibration" / "simulation_results.csv",
                res_dir / "model_b" / "best_individual_results.csv",
                res_dir / "model_b_results.csv",
                res_dir / "baseline_b_run" / "baseline_simulation_results.csv",
                res_dir / "baseline_b_run" / "sim_results.csv",
                res_dir / "baseline_b_run" / "simulation_results.csv",
            ]:
                if cand.exists():
                    model_b_csv = cand
                    break

            if model_a_csv and model_b_csv:
                df_a = pd.read_csv(model_a_csv)
                df_b = pd.read_csv(model_b_csv)
                pts, vars_list = process_pair(df_a, df_b)
                timeseries["available"] = True
                timeseries["points"] = pts
                timeseries["variables"] = vars_list
        except Exception as e:
            print(f"Error extracting time-series for {res_dir}: {e}")

        return timeseries

    def get_plot_path(self, case_id: str, mod_id: str, plot_name: str) -> Optional[Path]:
        """
        Locates the absolute path of a requested plot image.
        """
        case_detail = self.get_case_detail(case_id)
        mod_info = None
        if case_detail:
            modules = case_detail.get("modules", case_detail.get("experiments", []))
            mod_info = next((m for m in modules if m["id"] == mod_id), None)
        
        res_dir_rel = mod_info.get("results_dir", f"results/{case_id}/{mod_id}") if mod_info else f"results/{case_id}/{mod_id}"
        
        # Check in results_dir / plot_name or results_dir / plots / plot_name
        cand1 = self.root_dir / res_dir_rel / plot_name
        if cand1.exists() and cand1.is_file():
            return cand1
        cand2 = self.root_dir / res_dir_rel / "plots" / plot_name
        if cand2.exists() and cand2.is_file():
            return cand2
        return None
