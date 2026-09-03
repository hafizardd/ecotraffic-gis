export const EMISSION_DEFINITIONS = [
    { key: "tsp", field: "total_tsp_g_per_min", hourlyField: "total_tsp_kg_per_hr", label: "TSP", color: "#38bdf8" },
    { key: "nox", field: "total_nox_g_per_min", hourlyField: "total_nox_kg_per_hr", label: "NOx", color: "#f5a524" },
    { key: "so2", field: "total_so2_g_per_min", hourlyField: "total_so2_kg_per_hr", label: "SO₂", color: "#fb7185" },
    { key: "hc", field: "total_hc_g_per_min", hourlyField: "total_hc_kg_per_hr", label: "HC", color: "#a78bfa" },
    { key: "co", field: "total_co_g_per_min", hourlyField: "total_co_kg_per_hr", label: "CO", color: "#f05252" },
    { key: "co2", field: "total_co2_g_per_min", hourlyField: "total_co2_kg_per_hr", label: "CO₂", color: "#22c55e" },
    { key: "ch4", field: "total_ch4_g_per_min", hourlyField: "total_ch4_kg_per_hr", label: "CH₄", color: "#4c8dff" },
    { key: "n2o", field: "total_n2o_g_per_min", hourlyField: "total_n2o_kg_per_hr", label: "N₂O", color: "#e879f9" },
] as const;

export type EmissionKey = typeof EMISSION_DEFINITIONS[number]["key"];
export type EmissionField = typeof EMISSION_DEFINITIONS[number]["field"];
export type EmissionHourlyField = typeof EMISSION_DEFINITIONS[number]["hourlyField"];
