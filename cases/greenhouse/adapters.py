from __future__ import annotations
import openstudio
from calibration_framework.model_adapter import global_hook_registry


def substitute_greenhouse_parameters_osm(
    model: openstudio.model.Model,
    theta_1: float,
    theta_2: float,
    theta_3: float,
    theta_4: float,
    theta_5: float,
    theta_6: float,
    theta_7: float,
    theta_8: float,
    theta_9: float,
    theta_10: float,
) -> openstudio.model.Model:
    """
    Substitutes theta_1 (infiltration ACH), theta_2 (cladding U-value),
    theta_3 (inverter efficiency), theta_4 (pv active fraction), theta_5 (fan flow rate),
    theta_6 (roof U-value), theta_7 (roof SHGC), theta_8 (zone capacitance),
    theta_9 (equipment latent fraction), and theta_10 (window SHGC)
    into the OpenStudio Model.
    """
    # 1. Substitute Infiltration Rate (theta_1)
    for infil in model.getSpaceInfiltrationDesignFlowRates():
        infil.setAirChangesperHour(theta_1)

    # 2. Substitute Window U-Factor and SHGC (theta_2, theta_10)
    glazing_opt = model.getSimpleGlazingByName("Window Material")
    if glazing_opt.is_initialized():
        glazing = glazing_opt.get()
        glazing.setUFactor(theta_2)
        glazing.setSolarHeatGainCoefficient(theta_10)
        glazing.setVisibleTransmittance(theta_10)

    # 3. Substitute Inverter Efficiency (theta_3)
    for inverter in model.getElectricLoadCenterInverterSimples():
        inverter.setInverterEfficiency(theta_3)

    # 4. Substitute PV Active Fraction (theta_4)
    for perf in model.getPhotovoltaicPerformanceSimples():
        perf.setFractionOfSurfaceAreaWithActiveSolarCells(theta_4)

    # 5. Substitute Fan Flow Rate (theta_5)
    for fan in model.getFanZoneExhausts():
        fan.setMaximumFlowRate(theta_5)

    # 6. Substitute Roof U-Factor and SHGC (theta_6, theta_7)
    roof_glazing_opt = model.getSimpleGlazingByName("Roof Glazing Material")
    if roof_glazing_opt.is_initialized():
        roof_glazing = roof_glazing_opt.get()
        roof_glazing.setUFactor(theta_6)
        roof_glazing.setSolarHeatGainCoefficient(theta_7)
        roof_glazing.setVisibleTransmittance(theta_7)

    # 7. Substitute Zone Capacitance Multiplier (theta_8)
    zone_cap = model.getZoneCapacitanceMultiplierResearchSpecial()
    zone_cap.setTemperatureCapacityMultiplier(theta_8)

    # 8. Substitute Equipment Latent Fraction (theta_9)
    for equip_def in model.getElectricEquipmentDefinitions():
        equip_def.setFractionLatent(theta_9)

    return model


def apply_degradation_fault(
    model: openstudio.model.Model,
    infiltration_ach: float = 2.5,
    pv_active_fraction: float = 0.75,
) -> openstudio.model.Model:
    """Applies physical structural/equipment degradation faults to the greenhouse model."""
    for infil in model.getSpaceInfiltrationDesignFlowRates():
        infil.setAirChangesperHour(infiltration_ach)

    for perf in model.getPhotovoltaicPerformanceSimples():
        perf.setFractionOfSurfaceAreaWithActiveSolarCells(pv_active_fraction)

    return model


def apply_load_shift_schedule(model: openstudio.model.Model) -> openstudio.model.Model:
    """Applies night-peak load shift schedule (18:00 - 06:00 ON, 06:00 - 18:00 OFF)."""
    for sch in model.getScheduleRulesets():
        name = sch.nameString()
        if any(k in name for k in ["Lights_Schedule", "Fan_Schedule", "Pump_Schedule"]):
            d_sch = sch.defaultDaySchedule()
            d_sch.clearValues()
            d_sch.addValue(openstudio.Time(0, 6, 0, 0), 1.0)
            d_sch.addValue(openstudio.Time(0, 18, 0, 0), 0.0)
            d_sch.addValue(openstudio.Time(0, 24, 0, 0), 1.0)
    return model
