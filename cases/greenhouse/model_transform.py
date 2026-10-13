from __future__ import annotations
import os
from pathlib import Path
import openstudio
from calibration_framework.model_adapter import load_osm, save_osm

# Greenhouse Equipment Baseline Defaults
DEFAULT_PV_EFFICIENCY = 0.18
DEFAULT_INVERTER_EFFICIENCY = 0.90
DEFAULT_PV_ACTIVE_AREA = 0.95

DEFAULT_BATTERY_CAPACITY_KWH = 5.0
DEFAULT_BATTERY_MAX_POWER_W = 5000.0
DEFAULT_BATTERY_EFFICIENCY = 0.95

DEFAULT_LIGHTS_W_PER_M2 = 5.0
DEFAULT_PUMP_W_PER_M2 = 5.0
DEFAULT_FAN_MAX_FLOW_M3S = 0.5
DEFAULT_FAN_PRESSURE_RISE_PA = 125.0
DEFAULT_INFILTRATION_ACH = 0.5

DEFAULT_TIMESTEPS_PER_HOUR = 6
DEFAULT_SIMULATION_RUN_PERIOD = (7, 1, 7, 7)  # 7 days

LIGHTS_SCHEDULE = [
    (18, 0, 0.0),
    (22, 0, 1.0),
    (24, 0, 0.0),
]

FAN_SCHEDULE = [
    (9, 0, 0.0),
    (15, 0, 1.0),
    (24, 0, 0.0),
]

PUMP_SCHEDULE = [
    (6, 0, 0.0),
    (7, 0, 1.0),
    (18, 0, 0.0),
    (19, 0, 1.0),
    (24, 0, 0.0),
]


def extend_greenhouse_osm(
    input_osm_path: str | Path,
    output_osm_path: str | Path,
    default_pv_eff: float = DEFAULT_PV_EFFICIENCY,
    default_inverter_eff: float = DEFAULT_INVERTER_EFFICIENCY,
    timesteps_per_hour: int = DEFAULT_TIMESTEPS_PER_HOUR,
    run_period: tuple[int, int, int, int] = DEFAULT_SIMULATION_RUN_PERIOD,
) -> None:
    """
    Loads base greenhouse OSM, programmatically appends Infiltration, PV generators, Inverter,
    Battery storage, Lights, Fan, Pumps (ElectricEquipment), Schedules,
    and Output Variables using OpenStudio SDK, and saves as extended OSM.
    """
    model = load_osm(input_osm_path)

    # Set Simulation Timestep
    timestep = model.getTimestep()
    timestep.setNumberOfTimestepsPerHour(timesteps_per_hour)

    # Set Run Period
    rp = model.getRunPeriod()
    rp.setBeginMonth(run_period[0])
    rp.setBeginDayOfMonth(run_period[1])
    rp.setEndMonth(run_period[2])
    rp.setEndDayOfMonth(run_period[3])

    # 1. Discover roof/ceiling surfaces (fallback to sun-exposed walls if none)
    roof_surfaces = []
    for surface in model.getSurfaces():
        if surface.surfaceType().lower() == "roofceiling":
            roof_surfaces.append(surface)

    if not roof_surfaces:
        for surface in model.getSurfaces():
            if (
                surface.surfaceType().lower() == "wall"
                and surface.sunExposure().lower() == "sunexposed"
            ):
                roof_surfaces.append(surface)

    if not roof_surfaces:
        surfaces = list(model.getSurfaces())
        if surfaces:
            roof_surfaces = [surfaces[0]]

    # 2. Add Schedules using ScheduleRuleset
    lights_sch = openstudio.model.ScheduleRuleset(model)
    lights_sch.setName("Lights_Schedule")
    d_lights = lights_sch.defaultDaySchedule()
    for hour, minute, val in LIGHTS_SCHEDULE:
        d_lights.addValue(openstudio.Time(0, hour, minute, 0), val)

    fan_sch = openstudio.model.ScheduleRuleset(model)
    fan_sch.setName("Fan_Schedule")
    d_fan = fan_sch.defaultDaySchedule()
    for hour, minute, val in FAN_SCHEDULE:
        d_fan.addValue(openstudio.Time(0, hour, minute, 0), val)

    pump_sch = openstudio.model.ScheduleRuleset(model)
    pump_sch.setName("Pump_Schedule")
    d_pump = pump_sch.defaultDaySchedule()
    for hour, minute, val in PUMP_SCHEDULE:
        d_pump.addValue(openstudio.Time(0, hour, minute, 0), val)

    # 3. Add Infiltration, Lights, Exhaust Fan, Pump for each zone/space
    for zone in model.getThermalZones():
        zone_name = zone.nameString()

        for space in zone.spaces():
            infil = openstudio.model.SpaceInfiltrationDesignFlowRate(model)
            infil.setName(f"Infiltration_{space.nameString()}")
            infil.setAirChangesperHour(DEFAULT_INFILTRATION_ACH)
            infil.setSpace(space)

            lights_def = openstudio.model.LightsDefinition(model)
            lights_def.setName(f"Lights_Def_{space.nameString()}")
            lights_def.setWattsperSpaceFloorArea(DEFAULT_LIGHTS_W_PER_M2)

            lights = openstudio.model.Lights(lights_def)
            lights.setName(f"Lights_{space.nameString()}")
            lights.setSchedule(lights_sch)
            lights.setSpace(space)

            equip_def = openstudio.model.ElectricEquipmentDefinition(model)
            equip_def.setName(f"PumpMotor_Def_{space.nameString()}")
            equip_def.setWattsperSpaceFloorArea(DEFAULT_PUMP_W_PER_M2)

            equip = openstudio.model.ElectricEquipment(equip_def)
            equip.setName(f"PumpMotor_{space.nameString()}")
            equip.setSchedule(pump_sch)
            equip.setSpace(space)

        fan = openstudio.model.FanZoneExhaust(model)
        fan.setName(f"ExhaustFan_{zone_name}")
        fan.setMaximumFlowRate(DEFAULT_FAN_MAX_FLOW_M3S)
        fan.setPressureRise(DEFAULT_FAN_PRESSURE_RISE_PA)
        fan.setAvailabilitySchedule(fan_sch)
        fan.addToThermalZone(zone)

    # 4. Setup PV Performance & Generators
    elc = openstudio.model.ElectricLoadCenterDistribution(model)
    elc.setName("Electric Load Center")
    elc.setGeneratorOperationSchemeType("TrackElectrical")
    elc.setElectricalBussType("DirectCurrentWithInverterDCStorage")
    elc.setStorageOperationScheme("TrackFacilityElectricDemandStoreExcessOnSite")

    gen_idx = 0
    for roof in roof_surfaces:
        gen = openstudio.model.GeneratorPhotovoltaic.simple(model)
        gen.setName(f"PV_Gen_{gen_idx}")
        gen.setSurface(roof)

        perf = gen.photovoltaicPerformance().to_PhotovoltaicPerformanceSimple().get()
        perf.setName(f"PV_Perf_{gen_idx}")
        perf.setFractionOfSurfaceAreaWithActiveSolarCells(DEFAULT_PV_ACTIVE_AREA)
        perf.setFixedEfficiency(default_pv_eff)

        elc.addGenerator(gen)
        gen_idx += 1

    # 5. Inverter Simple
    inverter = openstudio.model.ElectricLoadCenterInverterSimple(model)
    inverter.setName("PV_Inverter")
    inverter.setInverterEfficiency(default_inverter_eff)
    elc.setInverter(inverter)

    # 6. Battery Storage Simple
    storage = openstudio.model.ElectricLoadCenterStorageSimple(model)
    storage.setName("Battery_Storage")
    storage.setMaximumStorageCapacity(DEFAULT_BATTERY_CAPACITY_KWH * 3600 * 1000)
    storage.setNominalEnergeticEfficiencyforCharging(DEFAULT_BATTERY_EFFICIENCY)
    storage.setNominalDischargingEnergeticEfficiency(DEFAULT_BATTERY_EFFICIENCY)
    storage.setMaximumPowerforDischarging(DEFAULT_BATTERY_MAX_POWER_W)
    storage.setMaximumPowerforCharging(DEFAULT_BATTERY_MAX_POWER_W)
    storage.setInitialStateofCharge(0.0)
    elc.setElectricalStorage(storage)

    # 7. Add Output Variables
    output_variables = [
        "Zone Air Temperature",
        "Electric Load Center Produced Electricity Rate",
        "Electric Storage Simple Charge State",
        "Generator Produced DC Electricity Rate",
        "Lights Electricity Rate",
        "Electric Equipment Electricity Rate",
        "Fan Electricity Rate",
        "Zone Windows Total Heat Gain Rate",
        "Surface Outside Face Temperature",
        "Zone Air Relative Humidity",
    ]
    for var_name in output_variables:
        var = openstudio.model.OutputVariable(var_name, model)
        var.setKeyValue("*")
        var.setReportingFrequency("Timestep")

    meters = [
        "Electricity:Facility",
        "ElectricityPurchased:Facility",
        "ElectricitySurplusSold:Facility",
    ]
    for m in meters:
        meter = openstudio.model.OutputMeter(model)
        meter.setName(m)
        meter.setReportingFrequency("Timestep")

    save_osm(model, output_osm_path)


def simplify_to_model_b(input_osm_path: str | Path, output_osm_path: str | Path) -> None:
    """
    Loads extended sawtooth OSM, automatically removes sawtooth roof spaces and zones,
    constructs a single flat roof for the main space, and adds an equivalent skylight.
    Saves as simplified Model B OSM.
    """
    model = load_osm(input_osm_path)

    main_space = None
    for space in model.getSpaces():
        if "roof" not in space.nameString().lower():
            main_space = space
            break

    roof_spaces = [
        space for space in model.getSpaces() if "roof" in space.nameString().lower()
    ]

    roof_construction = None
    for space in roof_spaces:
        for surface in space.surfaces():
            if (
                surface.surfaceType().lower() == "roofceiling"
                and surface.construction().is_initialized()
            ):
                roof_construction = surface.construction().get()
                break
        if roof_construction:
            break

    for space in roof_spaces:
        space.remove()

    for zone in model.getThermalZones():
        if "roof" in zone.nameString().lower():
            zone.remove()

    if main_space:
        roof_mat = openstudio.model.SimpleGlazing(model)
        roof_mat.setName("Roof Glazing Material")
        roof_mat.setUFactor(2.5)
        roof_mat.setVisibleTransmittance(0.8)
        roof_mat.setSolarHeatGainCoefficient(0.8)

        roof_const = openstudio.model.Construction(model)
        roof_const.setName("Roof Glazing Construction")
        roof_const.insertLayer(0, roof_mat)

        min_x = min_y = float("inf")
        max_x = max_y = float("-inf")
        max_z = float("-inf")
        has_walls = False
        for surface in main_space.surfaces():
            if surface.surfaceType().lower() == "wall":
                has_walls = True
                for v in surface.vertices():
                    min_x = min(min_x, v.x())
                    max_x = max(max_x, v.x())
                    min_y = min(min_y, v.y())
                    max_y = max(max_y, v.y())
                    max_z = max(max_z, v.z())

        if has_walls:
            points = openstudio.Point3dVector()
            points.append(openstudio.Point3d(max_x, min_y, max_z))
            points.append(openstudio.Point3d(max_x, max_y, max_z))
            points.append(openstudio.Point3d(min_x, max_y, max_z))
            points.append(openstudio.Point3d(min_x, min_y, max_z))
            roof = openstudio.model.Surface(points, model)
            roof.setSpace(main_space)
            roof.setSurfaceType("RoofCeiling")
            roof.setOutsideBoundaryCondition("Outdoors")
            if roof_construction:
                roof.setConstruction(roof_construction)

            cx = (max_x + min_x) / 2.0
            cy = (max_y + min_y) / 2.0
            cz = max_z

            scale = 0.896308
            sub_points = openstudio.Point3dVector()
            for p in points:
                nx = cx + (p.x() - cx) * scale
                ny = cy + (p.y() - cy) * scale
                nz = cz + (p.z() - cz) * scale
                sub_points.append(openstudio.Point3d(nx, ny, nz))

            sub = openstudio.model.SubSurface(sub_points, model)
            sub.setSurface(roof)
            sub.setSubSurfaceType("Skylight")
            sub.setConstruction(roof_const)
            sub.setName("Roof Skylight")

    save_osm(model, output_osm_path)
