// API service for handling data fetching and processing
export const API_BASE_URL =
  process.env.REACT_APP_API_BASE_URL || "http://localhost:8080/api";

// Type for processed data with dateObj
type WithDateObj<T> = T & { dateObj?: Date };

// Helper function to process timestamps in API responses
export const processTimestamps = <T>(data: T): T => {
  if (!data) return data;

  // Process arrays
  if (Array.isArray(data)) {
    return data.map((item) => processTimestamps(item)) as unknown as T;
  }

  // Process objects
  if (typeof data === "object" && data !== null) {
    const result = { ...data } as WithDateObj<T>;

    for (const key in result) {
      if (Object.prototype.hasOwnProperty.call(result, key)) {
        const value = result[key as keyof typeof result];

        // Convert timestamp fields to Date objects
        if (key === "timestamp" || key === "date" || key.endsWith("Date")) {
          if (
            typeof value === "number" ||
            (typeof value === "string" && !isNaN(Number(value)))
          ) {
            const timestamp = typeof value === "string" ? Number(value) : value;
            // Add dateObj for direct Date access
            result.dateObj = new Date(timestamp);
          } else if (typeof value === "string") {
            // Try to parse date strings
            const date = new Date(value);
            if (!isNaN(date.getTime())) {
              result.dateObj = date;
            }
          }
        } else if (typeof value === "object" && value !== null) {
          // Recursively process nested objects
          (result as any)[key] = processTimestamps(value);
        }
      }
    }

    return result as T;
  }

  return data;
};

// Fetch data with timestamp processing
export const fetchData = async <T>(endpoint: string): Promise<T> => {
  try {
    const response = await fetch(`${API_BASE_URL}${endpoint}`);
    if (!response.ok) {
      throw new Error(`HTTP error! Status: ${response.status}`);
    }
    const data = await response.json();
    return processTimestamps(data);
  } catch (error) {
    console.error(`Error fetching data from ${endpoint}:`, error);
    throw error;
  }
};

// API endpoints
export const getPositions = () => fetchData<any[]>("/positions");
export const getTrades = () => fetchData<any[]>("/trades");
export const getPerformance = () => fetchData<any>("/performance");
