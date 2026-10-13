from __future__ import annotations
import os
import json
import shutil
import time
import urllib.request
import urllib.parse
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator, Type
import pandas as pd

from calibration_framework.schemas import GroundTruthConfig, OutputMappingConfig
from calibration_framework.runner import EnergyPlusRunner
from calibration_framework.model_adapter import (
    load_osm,
    translate_model_to_idf,
)


@dataclass
class GroundTruthData:
    """
    Encapsulates reference / ground-truth observation dataset.
    Supports 2-tuple unpacking (df, execution_time) for backward compatibility.
    """
    df: pd.DataFrame
    execution_time: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def __iter__(self) -> Iterator[Any]:
        """Allows unpacking as `df, sim_time = ground_truth_data`."""
        yield self.df
        yield self.execution_time

    def __getitem__(self, index: int) -> Any:
        if index == 0:
            return self.df
        elif index == 1:
            return self.execution_time
        raise IndexError("GroundTruthData index out of range (valid: 0 for df, 1 for execution_time)")


class BaseGroundTruthProvider(ABC):
    """
    Abstract Base Class for supplying ground truth / reference datasets to modules and experiments.
    Decouples calibration & validation workflows from data provenance (Model A simulation, CSV files, Remote APIs, etc.).
    """

    def __init__(
        self,
        config: GroundTruthConfig,
        workspace_root: str | Path | None = None,
        force_rerun: bool = False,
    ):
        self.config = config
        self.workspace_root = Path(workspace_root).resolve() if workspace_root else Path.cwd().resolve()
        self.force_rerun = force_rerun

    def resolve_path(self, path: str | Path | None) -> Path | None:
        if path is None:
            return None
        p = Path(path)
        if p.is_absolute():
            return p
        return (self.workspace_root / p).resolve()

    def prepare_ground_truth(self) -> None:
        """Hook for offline model preparation, preprocessing, schema caching, or sensor synchronization."""
        pass

    @abstractmethod
    def get_truth_data(self, context: dict[str, Any] | None = None) -> GroundTruthData:
        """
        Retrieves reference ground truth dataset according to operational context.
        Context may contain scenario identifiers, modified models, date ranges, or fault conditions.
        """
        pass


class SimulationGroundTruthProvider(BaseGroundTruthProvider):
    """
    Virtual Ground Truth Provider based on high-fidelity simulation (e.g. Model A via EnergyPlus / OpenStudio).
    Executes EnergyPlus or reuses cached SQL/CSV simulation results.
    """

    def get_truth_data(self, context: dict[str, Any] | None = None) -> GroundTruthData:
        ctx = context or {}
        target_dir = ctx.get("target_dir")
        if target_dir is None:
            out_dir = self.config.output_dir or "results/ground_truth_simulation"
            target_dir = self.resolve_path(out_dir)
        else:
            target_dir = Path(target_dir)

        target_dir.mkdir(parents=True, exist_ok=True)
        time_a_file = target_dir / "sim_time.txt"

        # Check if modified IDF/OSM provided in context or from config
        idf_path = ctx.get("idf_path")
        osm_model = ctx.get("osm_model")
        epw_path = ctx.get("epw_path")
        output_mappings: list[OutputMappingConfig] | None = ctx.get("output_mappings")

        model_modifier_fn = ctx.get("model_modifier_fn")

        if idf_path is None:
            if osm_model is not None:
                if callable(model_modifier_fn):
                    model_modifier_fn(osm_model)
                idf_path = target_dir / "target.idf"
                translate_model_to_idf(osm_model, idf_path)
            elif self.config.extended_osm_path:
                ext_a_osm = self.resolve_path(self.config.extended_osm_path)
                if not ext_a_osm or not ext_a_osm.exists():
                    raise FileNotFoundError(f"Extended OSM model not found: {ext_a_osm}")
                model = load_osm(ext_a_osm)
                if callable(model_modifier_fn):
                    model_modifier_fn(model)
                idf_path = target_dir / "target.idf"
                translate_model_to_idf(model, idf_path)
            elif self.config.extended_idf_path:
                ext_a_idf = self.resolve_path(self.config.extended_idf_path)
                if not ext_a_idf or not ext_a_idf.exists():
                    raise FileNotFoundError(f"Extended IDF model not found: {ext_a_idf}")
                idf_path = target_dir / "target.idf"
                shutil.copy(ext_a_idf, idf_path)
            else:
                raise ValueError("SimulationGroundTruthProvider requires extended_idf_path or extended_osm_path")

        if epw_path is None:
            weather_path = ctx.get("weather_path")
            if weather_path:
                epw_path = Path(weather_path)
            else:
                raise ValueError("SimulationGroundTruthProvider requires epw_path in context")

        runner_a = EnergyPlusRunner(
            Path(idf_path),
            Path(epw_path),
            target_dir,
            output_mappings=output_mappings,
        )

        time_a: float | None = None
        sql_file = target_dir / "eplusout.sql"
        csv_file = target_dir / "target_results.csv"

        if sql_file.exists() and not self.force_rerun:
            df_true = runner_a.get_results()
            if time_a_file.exists():
                try:
                    time_a = float(time_a_file.read_text().strip())
                except Exception:
                    pass
        else:
            start_a = time.time()
            runner_a.run(mute=True)
            time_a = time.time() - start_a
            df_true = runner_a.get_results()
            df_true.to_csv(csv_file, index=False)
            time_a_file.write_text(f"{time_a:.4f}\n")

        if time_a is None:
            time_a = 1.0

        postprocess_fn = ctx.get("postprocess_fn")
        if callable(postprocess_fn):
            df_true = postprocess_fn(df_true)

        return GroundTruthData(
            df=df_true,
            execution_time=time_a,
            metadata={
                "source_type": "simulation",
                "provider": self.__class__.__name__,
                "target_dir": str(target_dir),
                "context": {k: v for k, v in ctx.items() if isinstance(v, (str, int, float, bool))},
            },
        )


class CsvGroundTruthProvider(BaseGroundTruthProvider):
    """
    CSV / File-based Ground Truth Provider.
    Reads ground truth timeseries from a local CSV file, with optional time filtering and resampling.
    """

    def get_truth_data(self, context: dict[str, Any] | None = None) -> GroundTruthData:
        ctx = context or {}
        data_path = ctx.get("data_path") or ctx.get("file_path") or self.config.data_path or self.config.file_path
        if not data_path:
            raise ValueError("CsvGroundTruthProvider requires 'data_path' or 'file_path' in GroundTruthConfig or context.")

        resolved_path = self.resolve_path(data_path)
        if not resolved_path or not resolved_path.exists():
            raise FileNotFoundError(f"Ground truth CSV dataset not found: {resolved_path}")

        start_time = time.time()
        df = pd.read_csv(resolved_path)

        timestamp_col = self.config.timestamp_col or "TimeIndex"
        if timestamp_col in df.columns:
            start_date = ctx.get("start_date")
            end_date = ctx.get("end_date")
            if start_date and end_date:
                df[timestamp_col] = pd.to_datetime(df[timestamp_col])
                df = df[(df[timestamp_col] >= pd.to_datetime(start_date)) & (df[timestamp_col] <= pd.to_datetime(end_date))]

        fetch_time = time.time() - start_time

        postprocess_fn = ctx.get("postprocess_fn")
        if callable(postprocess_fn):
            df = postprocess_fn(df)

        return GroundTruthData(
            df=df,
            execution_time=fetch_time,
            metadata={
                "source_type": "csv_file",
                "provider": self.__class__.__name__,
                "data_path": str(resolved_path),
            },
        )


# Alias for backward compatibility
PhysicalMeasurementProvider = CsvGroundTruthProvider


class RemoteApiGroundTruthProvider(BaseGroundTruthProvider):
    """
    Remote API Ground Truth Provider.
    Fetches reference observation time-series data from an external REST API or IoT endpoint.
    Supports HTTP GET/POST, JSON / CSV payload decoding, auth headers, and query parameters.
    """

    def get_truth_data(self, context: dict[str, Any] | None = None) -> GroundTruthData:
        ctx = context or {}
        api_url = ctx.get("api_url") or self.config.api_url
        if not api_url:
            raise ValueError("RemoteApiGroundTruthProvider requires 'api_url' in GroundTruthConfig or context.")

        method = (ctx.get("api_method") or self.config.api_method or "GET").upper()
        headers = dict(self.config.api_headers or {})
        if "api_headers" in ctx and isinstance(ctx["api_headers"], dict):
            headers.update(ctx["api_headers"])

        params = dict(self.config.api_params or {})
        if "api_params" in ctx and isinstance(ctx["api_params"], dict):
            params.update(ctx["api_params"])

        # Inject context temporal boundaries into query parameters if provided
        for date_key in ("start_date", "end_date", "start_time", "end_time"):
            if date_key in ctx:
                params[date_key] = str(ctx[date_key])

        timeout = ctx.get("api_timeout") or self.config.api_timeout or 30.0

        start_time = time.time()

        if method == "GET":
            if params:
                query_str = urllib.parse.urlencode(params)
                url_to_call = f"{api_url}?{query_str}" if "?" not in api_url else f"{api_url}&{query_str}"
            else:
                url_to_call = api_url
            req = urllib.request.Request(url_to_call, headers=headers, method="GET")
            with urllib.request.urlopen(req, timeout=timeout) as response:
                content_type = response.headers.get("Content-Type", "")
                raw_bytes = response.read()
        elif method == "POST":
            url_to_call = api_url
            headers.setdefault("Content-Type", "application/json")
            data_bytes = json.dumps(params).encode("utf-8")
            req = urllib.request.Request(url_to_call, data=data_bytes, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=timeout) as response:
                content_type = response.headers.get("Content-Type", "")
                raw_bytes = response.read()
        else:
            raise ValueError(f"Unsupported HTTP method '{method}' for RemoteApiGroundTruthProvider.")

        # Parse response into DataFrame
        text_data = raw_bytes.decode("utf-8", errors="replace")
        if "json" in content_type or text_data.strip().startswith(("{", "[")):
            parsed_json = json.loads(text_data)
            data_key = ctx.get("data_key") or self.config.data_key
            if data_key and isinstance(parsed_json, dict) and data_key in parsed_json:
                data_records = parsed_json[data_key]
            elif isinstance(parsed_json, list):
                data_records = parsed_json
            elif isinstance(parsed_json, dict) and "data" in parsed_json:
                data_records = parsed_json["data"]
            elif isinstance(parsed_json, dict) and "results" in parsed_json:
                data_records = parsed_json["results"]
            else:
                data_records = parsed_json
            df = pd.DataFrame(data_records)
        else:
            import io
            df = pd.read_csv(io.StringIO(text_data))

        fetch_time = time.time() - start_time

        postprocess_fn = ctx.get("postprocess_fn")
        if callable(postprocess_fn):
            df = postprocess_fn(df)

        return GroundTruthData(
            df=df,
            execution_time=fetch_time,
            metadata={
                "source_type": "remote_api",
                "provider": self.__class__.__name__,
                "api_url": api_url,
                "rows": len(df),
            },
        )


# Dynamic Provider Registry
GROUND_TRUTH_PROVIDERS: dict[str, Type[BaseGroundTruthProvider]] = {
    "simulation": SimulationGroundTruthProvider,
    "model_a": SimulationGroundTruthProvider,
    "energyplus": SimulationGroundTruthProvider,
    "csv": CsvGroundTruthProvider,
    "file": CsvGroundTruthProvider,
    "physical": CsvGroundTruthProvider,
    "measurement": CsvGroundTruthProvider,
    "sensor": CsvGroundTruthProvider,
    "model_p": CsvGroundTruthProvider,
    "api": RemoteApiGroundTruthProvider,
    "remote_api": RemoteApiGroundTruthProvider,
    "rest": RemoteApiGroundTruthProvider,
    "http": RemoteApiGroundTruthProvider,
}


def register_ground_truth_provider(type_name: str, provider_cls: Type[BaseGroundTruthProvider]) -> None:
    """Registers a custom Ground Truth Provider class for a specific type name."""
    GROUND_TRUTH_PROVIDERS[type_name.lower()] = provider_cls


def create_ground_truth_provider(
    config: GroundTruthConfig,
    workspace_root: str | Path | None = None,
    force_rerun: bool = False,
) -> BaseGroundTruthProvider:
    """Factory function for instantiating the appropriate BaseGroundTruthProvider."""
    gt_type = config.type.lower()
    provider_cls = GROUND_TRUTH_PROVIDERS.get(gt_type)
    if provider_cls is not None:
        return provider_cls(config, workspace_root=workspace_root, force_rerun=force_rerun)
    else:
        raise ValueError(
            f"Unknown ground truth provider type: '{config.type}'. "
            f"Available types: {list(GROUND_TRUTH_PROVIDERS.keys())}"
        )
