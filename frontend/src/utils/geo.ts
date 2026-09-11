// Geodesic circle as a closed GeoJSON polygon. Small enough that the
// spherical-earth approximation is plenty for a buffer visualization.
export function circlePolygon(center: [number, number], radiusMeters: number, steps = 64) {
    const [lon, lat] = center;
    const angular = radiusMeters / 6378137;
    const latRad = (lat * Math.PI) / 180;
    const lonRad = (lon * Math.PI) / 180;
    const ring: [number, number][] = [];
    for (let i = 0; i <= steps; i += 1) {
        const bearing = (i / steps) * 2 * Math.PI;
        const lat2 = Math.asin(
            Math.sin(latRad) * Math.cos(angular) + Math.cos(latRad) * Math.sin(angular) * Math.cos(bearing),
        );
        const lon2 = lonRad + Math.atan2(
            Math.sin(bearing) * Math.sin(angular) * Math.cos(latRad),
            Math.cos(angular) - Math.sin(latRad) * Math.sin(lat2),
        );
        ring.push([(lon2 * 180) / Math.PI, (lat2 * 180) / Math.PI]);
    }
    return { type: "Polygon" as const, coordinates: [ring] };
}

export function circleFeature(center: [number, number], radiusMeters: number) {
    return { type: "Feature" as const, geometry: circlePolygon(center, radiusMeters), properties: {} };
}
