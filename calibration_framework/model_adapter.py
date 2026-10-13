from __future__ import annotations
import os
from abc import ABC, abstractmethod
from typing import Any, Callable
from pathlib import Path
import openstudio

from calibration_framework.schemas import ParameterConfig, ParameterTarget

# Suppress OpenStudio internal warnings
openstudio.Logger.instance().standardOutLogger().setLogLevel(openstudio.Error)


def load_osm(osm_path: str | Path) -> openstudio.model.Model:
    """Loads an OSM file and returns the OpenStudio Model object."""
    osm_path_str = str(osm_path)
    if not os.path.exists(osm_path_str):
        raise FileNotFoundError(f"OSM file not found at {osm_path_str}")

    vt = openstudio.osversion.VersionTranslator()
    model_opt = vt.loadModel(openstudio.toPath(osm_path_str))
    if not model_opt.is_initialized():
        raise ValueError(f"Failed to load and parse OSM model at {osm_path_str}")
    model = model_opt.get()

    # Force instantiate built-in schedules to fix ScheduleTypeLimits warnings during translation
    model.alwaysOnDiscreteSchedule()
    model.alwaysOffDiscreteSchedule()
    model.alwaysOnContinuousSchedule()

    # Fix YearDescription warning
    yd = model.getYearDescription()
    yd.resetCalendarYear()

    return model


def save_osm(model: openstudio.model.Model, osm_path: str | Path) -> None:
    """Saves the OpenStudio Model object to an OSM file."""
    osm_path_str = str(osm_path)
    os.makedirs(os.path.dirname(os.path.abspath(osm_path_str)), exist_ok=True)
    model.save(openstudio.toPath(osm_path_str), True)


def translate_model_to_idf(model: openstudio.model.Model, idf_path: str | Path) -> None:
    """Translates an OpenStudio Model in memory to an EnergyPlus IDF file."""
    idf_path_str = str(idf_path)
    translator = openstudio.energyplus.ForwardTranslator()
    workspace = translator.translateModel(model)
    os.makedirs(os.path.dirname(os.path.abspath(idf_path_str)), exist_ok=True)
    workspace.save(openstudio.toPath(idf_path_str), True)


def translate_osm_to_idf(osm_path: str | Path, idf_path: str | Path) -> None:
    """Translates an OSM file into an EnergyPlus IDF file."""
    model = load_osm(osm_path)
    translate_model_to_idf(model, idf_path)


class HookRegistry:
    """Registry for domain-specific model mutation hooks."""

    def __init__(self):
        self._hooks: dict[str, Callable[[openstudio.model.Model, str, float], None]] = {}

    def register(self, name: str, func: Callable[[openstudio.model.Model, str, float], None]) -> None:
        self._hooks[name] = func

    def get(self, name: str) -> Callable[[openstudio.model.Model, str, float], None] | None:
        return self._hooks.get(name)


global_hook_registry = HookRegistry()


class BaseModelAdapter(ABC):
    """Abstract model adapter for applying candidate parameters into a building energy model."""

    @abstractmethod
    def apply_parameters(
        self, model: Any, parameters: dict[str, float] | list[float]
    ) -> Any:
        pass


class OpenStudioModelAdapter(BaseModelAdapter):
    """
    Generic OpenStudio parameter substitution engine.
    Reads declarative ParameterConfig definitions and applies values using OpenStudio SDK methods
    or registered custom domain hooks.
    """

    def __init__(
        self,
        parameters: list[ParameterConfig] | None = None,
        hook_registry: HookRegistry | None = None,
    ):
        self.model: openstudio.model.Model | None = None
        self.parameters = parameters or []
        self.param_map = {p.name: p for p in self.parameters}
        self.param_order = [p.name for p in self.parameters]
        self.hooks = hook_registry or global_hook_registry

    def set_parameters(self, parameters: list[ParameterConfig]) -> None:
        self.parameters = parameters
        self.param_map = {p.name: p for p in parameters}
        self.param_order = [p.name for p in parameters]

    def load(self, model_path: str | Path) -> openstudio.model.Model:
        """Loads an OpenStudio model from path into memory."""
        self.model = load_osm(model_path)
        return self.model

    def save_osm(self, osm_path: str | Path) -> None:
        """Saves current memory model to OSM."""
        if self.model is None:
            raise ValueError("No model loaded in adapter.")
        save_osm(self.model, osm_path)

    def save_idf(self, idf_path: str | Path) -> None:
        """Translates current memory model to IDF."""
        if self.model is None:
            raise ValueError("No model loaded in adapter.")
        translate_model_to_idf(self.model, idf_path)

    def apply_parameters(
        self,
        arg1: Any,
        arg2: Any = None,
        arg3: Any = None,
    ) -> openstudio.model.Model:
        """
        Applies candidate parameter values into an OpenStudio model instance.
        Supports:
          - apply_parameters(model, params)
          - apply_parameters(params, param_configs) (uses self.model)
          - apply_parameters(model, params, param_configs)
        """
        if isinstance(arg1, (list, dict)):
            if self.model is None:
                raise ValueError("No model loaded in adapter or passed to apply_parameters.")
            target_model = self.model
            params = arg1
            configs = arg2
        else:
            target_model = arg1
            params = arg2
            configs = arg3

        if configs is not None:
            self.set_parameters(configs)

        if isinstance(params, list):
            param_dict = dict(zip(self.param_order, params))
        elif isinstance(params, dict):
            param_dict = params
        else:
            param_dict = {}

        for name, value in param_dict.items():
            config = self.param_map.get(name)
            if not config or not config.target:
                continue

            target: ParameterTarget = config.target

            # 1. Custom hook execution if defined
            if target.hook_name:
                hook_fn = self.hooks.get(target.hook_name)
                if hook_fn:
                    hook_fn(target_model, name, value)
                    continue

            # 2. Declarative OpenStudio object resolution
            self._apply_declarative_target(target_model, target, value)

        return target_model

    def _apply_declarative_target(
        self,
        model: openstudio.model.Model,
        target: ParameterTarget,
        value: float,
    ) -> None:
        obj_type = target.object_type.lower()
        setter = target.setter
        name_filter = target.name_filter

        if "infiltration" in obj_type:
            for obj in model.getSpaceInfiltrationDesignFlowRates():
                if not name_filter or (name_filter.lower() in obj.nameString().lower()):
                    method = getattr(obj, setter, None)
                    if callable(method):
                        method(value)

        elif "simpleglazing" in obj_type or "glazing" in obj_type:
            if name_filter:
                glazing_opt = model.getSimpleGlazingByName(name_filter)
                if glazing_opt.is_initialized():
                    glazing = glazing_opt.get()
                    method = getattr(glazing, setter, None)
                    if callable(method):
                        method(value)
            else:
                for glazing in model.getSimpleGlazings():
                    method = getattr(glazing, setter, None)
                    if callable(method):
                        method(value)

        elif "inverter" in obj_type:
            for inv in model.getElectricLoadCenterInverterSimples():
                if not name_filter or (name_filter.lower() in inv.nameString().lower()):
                    method = getattr(inv, setter, None)
                    if callable(method):
                        method(value)

        elif "pv" in obj_type or "photovoltaic" in obj_type:
            for perf in model.getPhotovoltaicPerformanceSimples():
                if not name_filter or (name_filter.lower() in perf.nameString().lower()):
                    method = getattr(perf, setter, None)
                    if callable(method):
                        method(value)

        elif "fan" in obj_type:
            for fan in model.getFanZoneExhausts():
                if not name_filter or (name_filter.lower() in fan.nameString().lower()):
                    method = getattr(fan, setter, None)
                    if callable(method):
                        method(value)

        elif "capacitance" in obj_type or "multiplier" in obj_type:
            cap = model.getZoneCapacitanceMultiplierResearchSpecial()
            method = getattr(cap, setter, None)
            if callable(method):
                method(value)

        elif "equipment" in obj_type or "electricequipment" in obj_type:
            for equip in model.getElectricEquipmentDefinitions():
                if not name_filter or (name_filter.lower() in equip.nameString().lower()):
                    method = getattr(equip, setter, None)
                    if callable(method):
                        method(value)

        else:
            # Generic reflection fallback
            getter_name = f"get{target.object_type}s"
            getter = getattr(model, getter_name, None)
            if callable(getter):
                for item in getter():
                    if not name_filter or (name_filter.lower() in item.nameString().lower()):
                        method = getattr(item, setter, None)
                        if callable(method):
                            method(value)
