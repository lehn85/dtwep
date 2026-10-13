import {
  Thermometer,
  Sun,
  BatteryCharging,
  Zap,
  Droplets,
  Sparkles,
  Eye,
  Wind,
  Activity,
  Gauge,
  Flame,
  Layers,
  LucideIcon,
} from 'lucide-react';
import { VariableMeta } from '../types';

export interface ResolvedSignalConfig {
  id: string;
  label: string;
  unit: string;
  fullLabel: string;
  icon: LucideIcon;
  description?: string;
}

/**
 * Standard dictionary for common energy & building physics variables
 */
const KNOWN_VARIABLES: Record<string, { label: string; unit: string; icon: LucideIcon }> = {
  temp: { label: 'Zone Temp', unit: '°C', icon: Thermometer },
  temperature: { label: 'Zone Temp', unit: '°C', icon: Thermometer },
  t_glass: { label: 'Glass Surface Temp', unit: '°C', icon: Eye },
  t_out: { label: 'Outdoor Temp', unit: '°C', icon: Thermometer },
  t_soil: { label: 'Soil Temp', unit: '°C', icon: Thermometer },
  
  humidity: { label: 'Relative Humidity', unit: '%', icon: Droplets },
  rh: { label: 'Relative Humidity', unit: '%', icon: Droplets },
  moisture: { label: 'Moisture Level', unit: '%', icon: Droplets },
  
  pv: { label: 'PV Generation', unit: 'kW', icon: Sun },
  solar: { label: 'Solar Power', unit: 'kW', icon: Sun },
  indoor_solar: { label: 'Indoor Solar Gain', unit: 'W', icon: Sparkles },
  radiation: { label: 'Solar Radiation', unit: 'W/m²', icon: Sun },
  
  soc: { label: 'Battery SoC', unit: '%', icon: BatteryCharging },
  battery: { label: 'Battery State', unit: '%', icon: BatteryCharging },
  
  grid: { label: 'Net Grid Power', unit: 'kW', icon: Zap },
  grid_in: { label: 'Grid Import', unit: 'kW', icon: Zap },
  grid_out: { label: 'Grid Export', unit: 'kW', icon: Zap },
  power: { label: 'Electrical Power', unit: 'kW', icon: Zap },
  energy: { label: 'Energy Consumption', unit: 'kWh', icon: Zap },
  
  co2: { label: 'CO₂ Concentration', unit: 'ppm', icon: Wind },
  ventilation: { label: 'Ventilation Rate', unit: 'ACH', icon: Wind },
  infiltration: { label: 'Infiltration Rate', unit: 'ACH', icon: Wind },
  wind: { label: 'Wind Speed', unit: 'm/s', icon: Wind },
  pressure: { label: 'Pressure', unit: 'Pa', icon: Gauge },
  
  flow: { label: 'Flow Rate', unit: 'm³/h', icon: Activity },
  lux: { label: 'Illuminance', unit: 'lux', icon: Eye },
  heat: { label: 'Heating Power', unit: 'kW', icon: Flame },
  cooling: { label: 'Cooling Power', unit: 'kW', icon: Layers },
};

/**
 * Fuzzy icon detection for any variable name
 */
export function getIconForVariable(varKey: string): LucideIcon {
  const k = varKey.toLowerCase();
  if (k.includes('temp') || k.includes('deg') || k.includes('thermal')) return Thermometer;
  if (k.includes('humid') || k.includes('water') || k.includes('rain') || k.includes('droplet')) return Droplets;
  if (k.includes('pv') || k.includes('solar') || k.includes('sun') || k.includes('irradiance')) return Sun;
  if (k.includes('soc') || k.includes('batt') || k.includes('charge')) return BatteryCharging;
  if (k.includes('grid') || k.includes('power') || k.includes('elec') || k.includes('volt') || k.includes('current')) return Zap;
  if (k.includes('co2') || k.includes('air') || k.includes('wind') || k.includes('vent') || k.includes('infilt')) return Wind;
  if (k.includes('glass') || k.includes('lux') || k.includes('light') || k.includes('eye') || k.includes('optics')) return Eye;
  if (k.includes('flame') || k.includes('heat') || k.includes('burn') || k.includes('gas')) return Flame;
  if (k.includes('flow') || k.includes('press') || k.includes('gauge') || k.includes('speed')) return Gauge;
  if (k.includes('gain') || k.includes('flux') || k.includes('rad') || k.includes('star')) return Sparkles;
  return Activity;
}

/**
 * Extracts clean label and unit from strings like "Zone Temperature (°C)" or "Net Grid Power [kW]"
 */
export function parseLabelAndUnit(rawString: string): { label: string; unit: string } {
  if (!rawString) return { label: '', unit: '' };
  
  // Check parenthesis: "Label (Unit)"
  const parenMatch = rawString.match(/^(.*?)\s*\(([^)]+)\)\s*$/);
  if (parenMatch) {
    return {
      label: parenMatch[1].trim(),
      unit: parenMatch[2].trim(),
    };
  }

  // Check brackets: "Label [Unit]"
  const bracketMatch = rawString.match(/^(.*?)\s*\[([^\]]+)\]\s*$/);
  if (bracketMatch) {
    return {
      label: bracketMatch[1].trim(),
      unit: bracketMatch[2].trim(),
    };
  }

  return { label: rawString.trim(), unit: '' };
}

/**
 * Formats a variable key into a readable title (e.g. "cooling_demand_kw" -> "Cooling Demand Kw")
 */
export function humanizeVarKey(varKey: string): string {
  return varKey
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

/**
 * Resolves full metadata for a variable key dynamically, prioritizing
 * case/experiment config metadata and falling back to heuristics.
 */
export function resolveVariableConfig(
  varKey: string,
  configMetaMap?: Record<string, VariableMeta>,
  yLabelsMap?: Record<string, string>
): ResolvedSignalConfig {
  const normalizedKey = varKey.toLowerCase().trim();

  // 1. Direct match in configMetaMap
  if (configMetaMap && configMetaMap[varKey]) {
    const meta = configMetaMap[varKey];
    return {
      id: varKey,
      label: meta.label || humanizeVarKey(varKey),
      unit: meta.unit || '',
      fullLabel: meta.full_label || `${meta.label}${meta.unit ? ` (${meta.unit})` : ''}`,
      icon: getIconForVariable(varKey),
      description: meta.description,
    };
  }

  // 2. Match in yLabelsMap
  if (yLabelsMap && yLabelsMap[varKey]) {
    const rawLabel = yLabelsMap[varKey];
    const { label, unit } = parseLabelAndUnit(rawLabel);
    return {
      id: varKey,
      label: label || humanizeVarKey(varKey),
      unit: unit,
      fullLabel: rawLabel,
      icon: getIconForVariable(varKey),
    };
  }

  // 3. Match in KNOWN_VARIABLES dictionary
  if (KNOWN_VARIABLES[normalizedKey]) {
    const known = KNOWN_VARIABLES[normalizedKey];
    return {
      id: varKey,
      label: known.label,
      unit: known.unit,
      fullLabel: `${known.label} (${known.unit})`,
      icon: known.icon,
    };
  }

  // 4. Default fallback: generate readable label and smart icon
  const humanLabel = humanizeVarKey(varKey);
  const { label, unit } = parseLabelAndUnit(humanLabel);
  return {
    id: varKey,
    label: label,
    unit: unit,
    fullLabel: humanLabel,
    icon: getIconForVariable(varKey),
  };
}
