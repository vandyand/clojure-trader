import axios, { AxiosError, AxiosRequestConfig } from "axios";

// Define base API URL based on environment
const API_URL = process.env.REACT_APP_API_URL || "http://localhost:3001/api";

// Create axios instance with default config
const apiClient = axios.create({
  baseURL: API_URL,
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 10000,
});

// Add request interceptor for auth tokens (if needed)
apiClient.interceptors.request.use(
  (config) => {
    // You can add auth token logic here if needed
    return config;
  },
  (error) => Promise.reject(error)
);

// Add response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    // Customize error handling here
    if (error.response) {
      // The request was made and the server responded with a status code
      // that falls out of the range of 2xx
      console.error("API Error:", error.response.status, error.response.data);
    } else if (error.request) {
      // The request was made but no response was received
      console.error("Network Error:", error.message);
    } else {
      // Something happened in setting up the request that triggered an Error
      console.error("Request Error:", error.message);
    }
    return Promise.reject(error);
  }
);

// Define common request wrapper
const request = async <T>(config: AxiosRequestConfig): Promise<T> => {
  try {
    const response = await apiClient(config);
    return response.data;
  } catch (error) {
    throw error;
  }
};

// Export request methods
export const api = {
  get: <T>(url: string, params?: any) =>
    request<T>({ method: "get", url, params }),

  post: <T>(url: string, data?: any) =>
    request<T>({ method: "post", url, data }),

  put: <T>(url: string, data?: any) => request<T>({ method: "put", url, data }),

  delete: <T>(url: string) => request<T>({ method: "delete", url }),
};

export default api;
