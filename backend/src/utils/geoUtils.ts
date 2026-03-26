/**
 * Calculates the distance between two geographic points using the Haversine formula
 * @param lat1 Latitude of first point
 * @param lon1 Longitude of first point
 * @param lat2 Latitude of second point
 * @param lon2 Longitude of second point
 * @returns Distance in kilometers
 */
export function calculateDistance(
  lat1: number,
  lon1: number,
  lat2: number,
  lon2: number
): number {
  const R = 6371; // Earth's radius in kilometers
  const dLat = toRad(lat2 - lat1);
  const dLon = toRad(lon2 - lon1);
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(toRad(lat1)) *
      Math.cos(toRad(lat2)) *
      Math.sin(dLon / 2) *
      Math.sin(dLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c;
}

/**
 * Calculates the geographic centroid (center point) of an array of coordinates
 * @param coordinates Array of coordinate objects with lat and long properties
 * @returns Centroid point or null if empty array
 */
export function calculateCentroid(
  coordinates: Array<{ lat: number; long: number }>
): { lat: number; long: number } | null {
  if (coordinates.length === 0) {
    return null;
  }

  let totalLat = 0;
  let totalLong = 0;

  for (const coord of coordinates) {
    totalLat += coord.lat;
    totalLong += coord.long;
  }

  return {
    lat: totalLat / coordinates.length,
    long: totalLong / coordinates.length,
  };
}

/**
 * Converts degrees to radians
 * @param degrees Value in degrees
 * @returns Value in radians
 */
function toRad(degrees: number): number {
  return degrees * (Math.PI / 180);
}

