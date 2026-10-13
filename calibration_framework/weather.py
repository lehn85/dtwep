from __future__ import annotations
import os
import json
import shutil
import hashlib
import urllib.request
import urllib.parse
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator, Type
import pandas as pd

from calibration_framework.schemas import WeatherConfig


# EPW Standard Column Names for data lines (excluding 8 header rows)
EPW_COLUMN_NAMES = [
    "Year", "Month", "Day", "Hour", "Minute",
    "Data_Source_and_Uncertainty_Flags",
    "DryBulb", "DewPoint", "RelHum", "AtmPressure",
    "ExtHorzRad", "ExtDirRad", "HorzIRSky", "GloHorzRad", "DirNormRad", "DifHorzRad",
    "GloHorzIllum", "DirNormIllum", "DifHorzIllum", "ZenLum",
    "WindDir", "WindSpeed", "TotSkyCover", "OpaqSkyCover",
    "Visibility", "CeilingHgt", "PresWeathObs", "PresWeathCodes",
    "PrecipWater", "AerOptDepth", "SnowDepth", "DaysLastSnow",
    "Albedo", "LiquidPrecipDepth", "LiquidPrecipRate"
]


@dataclass
class WeatherData:
    """
    Encapsulates resolved weather dataset and its underlying EPW file path.
    Supports unpacking / iteration as `epw_path, df = weather_data`.
    """
    epw_path: Path
    df: pd.DataFrame | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __iter__(self) -> Iterator[Any]:
        yield self.epw_path
        yield self.df

    def __getitem__(self, index: int) -> Any:
        if index == 0:
            return self.epw_path
        elif index == 1:
            return self.df
        raise IndexError("WeatherData index out of range (valid: 0 for epw_path, 1 for df)")


def read_epw_dataframe(epw_path: str | Path) -> pd.DataFrame:
    """Reads an EPW file into a pandas DataFrame (skipping first 8 metadata header lines)."""
    p = Path(epw_path)
    if not p.exists():
        raise FileNotFoundError(f"EPW file not found: {p.resolve()}")
    df = pd.read_csv(p, skiprows=8, header=None, names=EPW_COLUMN_NAMES)
    return df


class BaseWeatherProvider(ABC):
    """
    Abstract Base Class for supplying weather boundary conditions (EPW files)
    to simulation engines, calibration optimizers, and multi-scenario experiments.
    """

    def __init__(
        self,
        config: WeatherConfig | dict[str, Any],
        workspace_root: str | Path | None = None,
        cache_dir: str | Path | None = None,
    ):
        if isinstance(config, dict):
            self.config = WeatherConfig.from_dict(config)
        elif isinstance(config, WeatherConfig):
            self.config = config
        else:
            raise TypeError(f"Expected WeatherConfig or dict, got {type(config)}")

        self.workspace_root = Path(workspace_root).resolve() if workspace_root else Path.cwd().resolve()
        self.cache_dir = Path(cache_dir).resolve() if cache_dir else (self.workspace_root / "results" / ".weather_cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def resolve_path(self, path: str | Path | None) -> Path | None:
        if path is None:
            return None
        p = Path(path)
        if p.is_absolute():
            return p
        return (self.workspace_root / p).resolve()

    @abstractmethod
    def get_weather_file(self, context: dict[str, Any] | None = None) -> Path:
        """
        Resolves or generates the EPW weather file path according to the operational context.
        Context may specify scenario names, weather keys, date ranges, or dynamic modifiers.
        """
        pass

    def get_weather_data(self, context: dict[str, Any] | None = None) -> WeatherData:
        """
        Returns a WeatherData object containing the resolved EPW file path and its parsed DataFrame.
        """
        epw_path = self.get_weather_file(context)
        df = read_epw_dataframe(epw_path) if epw_path.exists() else None
        return WeatherData(
            epw_path=epw_path,
            df=df,
            metadata={
                "provider": self.__class__.__name__,
                "provider_type": self.config.type,
                "context": {k: str(v) for k, v in (context or {}).items() if not callable(v)},
            },
        )


class FileWeatherProvider(BaseWeatherProvider):
    """
    Standard File-based Weather Provider.
    Resolves static EPW files (e.g. TMY/TMYx) from predefined file paths or multi-scenario dictionaries.
    """

    def get_weather_file(self, context: dict[str, Any] | None = None) -> Path:
        ctx = context or {}
        scenario = ctx.get("scenario")
        weather_key = (
            ctx.get("weather_key")
            or (getattr(scenario, "weather_key", None) if scenario else None)
            or ctx.get("key")
            or "standard"
        )

        target_path: str | Path | None = None

        # 1. Check direct epw_path in context
        if "epw_path" in ctx and ctx["epw_path"]:
            target_path = ctx["epw_path"]

        # 2. Check files dictionary in config
        elif self.config.files and weather_key in self.config.files:
            target_path = self.config.files[weather_key]
        elif self.config.files and "default" in self.config.files:
            target_path = self.config.files["default"]
        elif self.config.files and "standard" in self.config.files:
            target_path = self.config.files["standard"]

        # 3. Check direct epw_path or base_epw in config
        elif self.config.epw_path:
            target_path = self.config.epw_path
        elif self.config.base_epw:
            target_path = self.config.base_epw

        # 4. Fallback to any file in files dictionary
        elif self.config.files:
            target_path = next(iter(self.config.files.values()))

        if not target_path:
            raise ValueError(
                f"FileWeatherProvider could not resolve EPW file for weather_key='{weather_key}'. "
                f"Available files: {list(self.config.files.keys()) if self.config.files else 'None'}"
            )

        resolved = self.resolve_path(target_path)
        if not resolved or not resolved.exists():
            raise FileNotFoundError(f"Weather EPW file not found: {resolved}")
        return resolved


class SyntheticWeatherProvider(BaseWeatherProvider):
    """
    Synthetic / Programmatic Weather Provider for What-If Analysis & Extreme Scenarios.
    Applies numerical transformations (temperature shifts, solar scaling, wind adjustments)
    to a base EPW file on-the-fly and caches the modified EPW file.
    """

    def get_weather_file(self, context: dict[str, Any] | None = None) -> Path:
        ctx = context or {}
        base_path = (
            ctx.get("base_epw")
            or self.config.base_epw
            or self.config.epw_path
            or (self.config.files.get("standard") if self.config.files else None)
        )
        if not base_path:
            raise ValueError("SyntheticWeatherProvider requires 'base_epw' or 'epw_path' to apply modifications.")

        resolved_base = self.resolve_path(base_path)
        if not resolved_base or not resolved_base.exists():
            raise FileNotFoundError(f"Base EPW file for synthetic modification not found: {resolved_base}")

        # Extract shift / perturbation parameters
        temp_shift = float(ctx.get("temp_shift", self.config.temp_shift))
        dew_point_shift = float(ctx.get("dew_point_shift", getattr(self.config, "dew_point_shift", temp_shift)))
        solar_multiplier = float(ctx.get("solar_multiplier", self.config.solar_multiplier))
        wind_multiplier = float(ctx.get("wind_multiplier", getattr(self.config, "wind_multiplier", 1.0)))

        # If no transformations needed, return base directly
        if temp_shift == 0.0 and dew_point_shift == 0.0 and solar_multiplier == 1.0 and wind_multiplier == 1.0:
            return resolved_base

        # Create unique cached filename based on modification parameters
        param_sig = f"T_{temp_shift:+.1f}_Td_{dew_point_shift:+.1f}_S_{solar_multiplier:.2f}_W_{wind_multiplier:.2f}"
        hash_suffix = hashlib.md5(param_sig.encode("utf-8")).hexdigest()[:8]
        out_filename = f"synthetic_{resolved_base.stem}_{param_sig}_{hash_suffix}.epw"
        out_path = self.cache_dir / out_filename

        if out_path.exists():
            return out_path

        # Generate modified EPW file
        self._apply_epw_transformations(
            input_epw=resolved_base,
            output_epw=out_path,
            temp_shift=temp_shift,
            dew_point_shift=dew_point_shift,
            solar_multiplier=solar_multiplier,
            wind_multiplier=wind_multiplier,
        )
        return out_path

    @staticmethod
    def _apply_epw_transformations(
        input_epw: Path,
        output_epw: Path,
        temp_shift: float = 0.0,
        dew_point_shift: float = 0.0,
        solar_multiplier: float = 1.0,
        wind_multiplier: float = 1.0,
    ) -> None:
        with open(input_epw, "r", encoding="utf-8") as f:
            lines = f.readlines()

        headers = lines[:8]
        data_lines = lines[8:]
        modified_lines = []

        for line in data_lines:
            parts = line.strip().split(",")
            if len(parts) >= 22:
                try:
                    # Index 6: Dry Bulb Temperature (°C)
                    # Index 7: Dew Point Temperature (°C)
                    # Index 13: Global Horizontal Radiation (Wh/m2)
                    # Index 14: Direct Normal Radiation (Wh/m2)
                    # Index 15: Diffuse Horizontal Radiation (Wh/m2)
                    # Index 21: Wind Speed (m/s)
                    if temp_shift != 0.0:
                        parts[6] = f"{float(parts[6]) + temp_shift:.1f}"
                    if dew_point_shift != 0.0:
                        parts[7] = f"{float(parts[7]) + dew_point_shift:.1f}"
                    if solar_multiplier != 1.0:
                        parts[13] = f"{max(0.0, float(parts[13]) * solar_multiplier):.0f}"
                        parts[14] = f"{max(0.0, float(parts[14]) * solar_multiplier):.0f}"
                        parts[15] = f"{max(0.0, float(parts[15]) * solar_multiplier):.0f}"
                    if wind_multiplier != 1.0:
                        parts[21] = f"{max(0.0, float(parts[21]) * wind_multiplier):.1f}"
                except ValueError:
                    pass
            modified_lines.append(",".join(parts) + "\n")

        with open(output_epw, "w", encoding="utf-8", newline="") as f:
            f.writelines(headers)
            f.writelines(modified_lines)


class StationMeasurementWeatherProvider(BaseWeatherProvider):
    """
    On-Site / Weather Station Measurement Provider.
    Injects physical observation time-series (from local AWS CSV or IoT sensor loggers)
    into a reference template EPW file to drive physical digital twin calibration.
    """

    def get_weather_file(self, context: dict[str, Any] | None = None) -> Path:
        ctx = context or {}
        data_path = ctx.get("data_path") or self.config.data_path
        template_epw = (
            ctx.get("base_template_epw")
            or ctx.get("base_epw")
            or self.config.base_template_epw
            or self.config.base_epw
            or self.config.epw_path
        )

        if not data_path:
            raise ValueError("StationMeasurementWeatherProvider requires 'data_path' (CSV station measurements).")
        if not template_epw:
            raise ValueError("StationMeasurementWeatherProvider requires 'base_template_epw' or 'base_epw'.")

        resolved_csv = self.resolve_path(data_path)
        resolved_template = self.resolve_path(template_epw)

        if not resolved_csv or not resolved_csv.exists():
            raise FileNotFoundError(f"Station measurement CSV not found: {resolved_csv}")
        if not resolved_template or not resolved_template.exists():
            raise FileNotFoundError(f"Template EPW file not found: {resolved_template}")

        # Unique hash for station data integration
        csv_mtime = str(resolved_csv.stat().st_mtime)
        hash_suffix = hashlib.md5(f"{resolved_csv}_{csv_mtime}".encode("utf-8")).hexdigest()[:8]
        out_path = self.cache_dir / f"station_{resolved_template.stem}_{hash_suffix}.epw"

        if out_path.exists():
            return out_path

        # Inject CSV measurements into EPW template
        df_station = pd.read_csv(resolved_csv)
        self._inject_station_data(resolved_template, df_station, out_path, self.config.column_mappings or {})
        return out_path

    @staticmethod
    def _inject_station_data(
        template_epw: Path,
        df_station: pd.DataFrame,
        output_epw: Path,
        mappings: dict[str, str],
    ) -> None:
        with open(template_epw, "r", encoding="utf-8") as f:
            lines = f.readlines()

        headers = lines[:8]
        data_lines = lines[8:]
        n_records = min(len(data_lines), len(df_station))

        # Standard field mapping fallbacks
        col_dry_bulb = mappings.get("dry_bulb") or mappings.get("temperature") or "dry_bulb"
        col_rel_hum = mappings.get("rel_hum") or mappings.get("humidity") or "rel_hum"
        col_solar = mappings.get("solar") or mappings.get("ghi") or "glo_horz_rad"
        col_wind = mappings.get("wind_speed") or mappings.get("wind") or "wind_speed"

        modified_lines = []
        for i in range(len(data_lines)):
            parts = data_lines[i].strip().split(",")
            if i < n_records and len(parts) >= 22:
                row = df_station.iloc[i]
                if col_dry_bulb in row and pd.notna(row[col_dry_bulb]):
                    parts[6] = f"{float(row[col_dry_bulb]):.1f}"
                if col_rel_hum in row and pd.notna(row[col_rel_hum]):
                    parts[8] = f"{float(row[col_rel_hum]):.0f}"
                if col_solar in row and pd.notna(row[col_solar]):
                    parts[13] = f"{float(row[col_solar]):.0f}"
                if col_wind in row and pd.notna(row[col_wind]):
                    parts[21] = f"{float(row[col_wind]):.1f}"
            modified_lines.append(",".join(parts) + "\n")

        with open(output_epw, "w", encoding="utf-8", newline="") as f:
            f.writelines(headers)
            f.writelines(modified_lines)


class RemoteApiWeatherProvider(BaseWeatherProvider):
    """
    Remote API Weather Provider.
    Fetches real-time, historical reanalysis, or forecast meteorological data
    from external REST APIs (e.g. Open-Meteo, ECMWF, NOAA) and compiles into a valid EPW file.
    """

    def get_weather_file(self, context: dict[str, Any] | None = None) -> Path:
        ctx = context or {}
        api_url = ctx.get("api_url") or self.config.api_url
        template_epw = (
            ctx.get("base_template_epw")
            or ctx.get("base_epw")
            or self.config.base_template_epw
            or self.config.base_epw
            or self.config.epw_path
        )

        if not api_url:
            raise ValueError("RemoteApiWeatherProvider requires 'api_url' in WeatherConfig or context.")
        if not template_epw:
            raise ValueError("RemoteApiWeatherProvider requires 'base_template_epw' or 'base_epw' to structure EPW output.")

        resolved_template = self.resolve_path(template_epw)
        if not resolved_template or not resolved_template.exists():
            raise FileNotFoundError(f"Template EPW file not found: {resolved_template}")

        params = dict(self.config.api_params or {})
        if "api_params" in ctx and isinstance(ctx["api_params"], dict):
            params.update(ctx["api_params"])

        # URL Query encoding
        query_str = urllib.parse.urlencode(params) if params else ""
        full_url = f"{api_url}?{query_str}" if query_str else api_url
        hash_suffix = hashlib.md5(full_url.encode("utf-8")).hexdigest()[:8]
        out_path = self.cache_dir / f"api_{resolved_template.stem}_{hash_suffix}.epw"

        if out_path.exists():
            return out_path

        # Perform HTTP GET request
        req = urllib.request.Request(
            full_url,
            headers=dict(self.config.api_headers or {}),
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=self.config.api_timeout or 30.0) as resp:
            raw_text = resp.read().decode("utf-8", errors="replace")

        # Parse response
        parsed = json.loads(raw_text)
        # Check standard Open-Meteo format or generic hourly dataframe
        if "hourly" in parsed and isinstance(parsed["hourly"], dict):
            df_api = pd.DataFrame(parsed["hourly"])
        else:
            df_api = pd.DataFrame(parsed)

        # Standardize column names if needed
        StationMeasurementWeatherProvider._inject_station_data(
            template_epw=resolved_template,
            df_station=df_api,
            output_epw=out_path,
            mappings=self.config.column_mappings or {},
        )
        return out_path


# Dynamic Weather Provider Registry
WEATHER_PROVIDERS: dict[str, Type[BaseWeatherProvider]] = {
    "file": FileWeatherProvider,
    "epw": FileWeatherProvider,
    "static": FileWeatherProvider,
    "tmy": FileWeatherProvider,
    "synthetic": SyntheticWeatherProvider,
    "modified": SyntheticWeatherProvider,
    "what_if": SyntheticWeatherProvider,
    "extreme": SyntheticWeatherProvider,
    "station": StationMeasurementWeatherProvider,
    "station_csv": StationMeasurementWeatherProvider,
    "measurement": StationMeasurementWeatherProvider,
    "aws": StationMeasurementWeatherProvider,
    "api": RemoteApiWeatherProvider,
    "remote_api": RemoteApiWeatherProvider,
    "forecast": RemoteApiWeatherProvider,
}


def register_weather_provider(type_name: str, provider_cls: Type[BaseWeatherProvider]) -> None:
    """Registers a custom Weather Provider class for a specific type name."""
    WEATHER_PROVIDERS[type_name.lower()] = provider_cls


def create_weather_provider(
    config: WeatherConfig | dict[str, Any] | str | Path | None,
    workspace_root: str | Path | None = None,
    cache_dir: str | Path | None = None,
) -> BaseWeatherProvider:
    """
    Factory function for instantiating the appropriate BaseWeatherProvider.
    Supports WeatherConfig, dictionaries, direct file path strings, or None.
    """
    if config is None:
        cfg = WeatherConfig(type="file")
    elif isinstance(config, (str, Path)):
        cfg = WeatherConfig(type="file", epw_path=str(config))
    elif isinstance(config, dict):
        cfg = WeatherConfig.from_dict(config)
    elif isinstance(config, WeatherConfig):
        cfg = config
    else:
        raise TypeError(f"Invalid weather configuration type: {type(config)}")

    w_type = cfg.type.lower()
    provider_cls = WEATHER_PROVIDERS.get(w_type)
    if provider_cls is not None:
        return provider_cls(cfg, workspace_root=workspace_root, cache_dir=cache_dir)
    else:
        raise ValueError(
            f"Unknown weather provider type: '{cfg.type}'. "
            f"Available types: {list(WEATHER_PROVIDERS.keys())}"
        )
