/**
 * Parses a UTC datetime string from the backend.
 * The backend stores naive datetimes (no timezone suffix).
 * We append 'Z' if missing so JavaScript treats it as UTC, not local time.
 */
export function parseUtc(dateString: string): Date {
  if (!dateString) return new Date();
  
  // If it already has Z or a timezone offset like +HH:MM or -HH:MM after the time separator 'T'
  const hasTimezone = dateString.includes('Z') || 
                      (dateString.includes('T') && 
                       (dateString.lastIndexOf('+') > dateString.indexOf('T') || 
                        dateString.lastIndexOf('-') > dateString.indexOf('T')));
                      
  if (hasTimezone) {
    return new Date(dateString);
  }
  
  // Append Z to mark naive datetimes as UTC
  return new Date(dateString + 'Z');
}
