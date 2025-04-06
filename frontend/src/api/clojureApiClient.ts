import axios from "axios";
import {
  Account,
  Position,
  Performance,
  BacktestResult,
  BacktestDetail,
} from "./tradingService";

// Constants
const CLOJURE_API_URL =
  process.env.REACT_APP_CLOJURE_API_URL ||
  "https://clojure-trader-api-18279899daf7.herokuapp.com";

// Create axios instance with default config
const clojureClient = axios.create({
  baseURL: CLOJURE_API_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

// Add request interceptor to include auth token if available
clojureClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("auth_token");
    if (token) {
      config.headers["Authorization"] = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Add response interceptor to process the response format
clojureClient.interceptors.response.use(
  (response) => {
    // Check if the response has the expected format { status: "success", data: ... }
    if (response.data && response.data.status === "success") {
      // Extract the data property
      return { ...response, data: response.data.data };
    }
    return response;
  },
  (error) => {
    // Process API error responses
    if (
      error.response &&
      error.response.data &&
      error.response.data.status === "error"
    ) {
      console.error("API Error:", error.response.data.message);

      // If unauthorized, clear auth token
      if (error.response.status === 401) {
        localStorage.removeItem("auth_token");
        localStorage.removeItem("auth_user");
        // Redirect to login page if needed
        // window.location.href = '/login';
      }

      return Promise.reject(new Error(error.response.data.message));
    }
    return Promise.reject(error);
  }
);

// Helper to parse API response
const processResponse = <T>(response: any): T => {
  return response.data;
};

// Auth methods
export const authService = {
  login: async (username: string, password: string) => {
    try {
      const response = await axios.post(`${CLOJURE_API_URL}/api/auth/login`, {
        username,
        password,
      });
      return response.data;
    } catch (error) {
      console.error("Login error:", error);
      throw error;
    }
  },

  register: async (username: string, password: string, email: string) => {
    try {
      const response = await axios.post(
        `${CLOJURE_API_URL}/api/auth/register`,
        {
          username,
          password,
          email,
        }
      );
      return response.data;
    } catch (error) {
      console.error("Registration error:", error);
      throw error;
    }
  },

  getProfile: async () => {
    try {
      const response = await clojureClient.get("/api/auth/profile");
      return processResponse(response);
    } catch (error) {
      console.error("Error fetching profile:", error);
      throw error;
    }
  },
};

export const clojureApiService = {
  // Auth service
  auth: authService,

  // Account endpoints
  getAccounts: async (): Promise<Account[]> => {
    try {
      const response = await clojureClient.get("/api/v1/accounts");
      return processResponse<Account[]>(response);
    } catch (error) {
      console.error("Error fetching accounts:", error);
      throw error;
    }
  },

  getAccountSummary: async (accountId?: string): Promise<Account> => {
    try {
      const endpoint = accountId
        ? `/api/v1/account-summary/${accountId}`
        : "/api/v1/account-summary";
      const response = await clojureClient.get(endpoint);
      return processResponse<Account>(response);
    } catch (error) {
      console.error("Error fetching account summary:", error);
      throw error;
    }
  },

  getAccountsWorth: async (): Promise<{
    oanda: number;
    binance: number;
    total: number;
    timestamp: number;
  }> => {
    try {
      const accounts = await clojureApiService.getAccounts();
      const totalValue = accounts.reduce(
        (sum, account) => sum + (account.nav || account.balance || 0),
        0
      );

      return {
        oanda: totalValue, // Assuming all accounts are from Oanda for now
        binance: 0, // Not implemented yet
        total: totalValue,
        timestamp: Date.now(),
      };
    } catch (error) {
      console.error("Error calculating accounts worth:", error);
      throw error;
    }
  },

  // Position endpoints
  getPositions: async (): Promise<Position[]> => {
    try {
      const endpoint = "/api/v1/open-positions";
      const response = await clojureClient.get(endpoint);
      return processResponse<Position[]>(response);
    } catch (error) {
      console.error("Error fetching positions:", error);
      throw error;
    }
  },

  getPositionsByAccount: async (accountId: string): Promise<Position[]> => {
    try {
      const endpoint = `/api/v1/open-positions/${accountId}`;
      const response = await clojureClient.get(endpoint);
      return processResponse<Position[]>(response);
    } catch (error) {
      console.error(
        `Error fetching positions for account ${accountId}:`,
        error
      );
      throw error;
    }
  },

  getOpenTrades: async (): Promise<any[]> => {
    try {
      const response = await clojureClient.get("/api/v1/open-trades");
      return processResponse<any[]>(response);
    } catch (error) {
      console.error("Error fetching open trades:", error);
      throw error;
    }
  },

  // Performance endpoints
  getPerformance: async (days: number = 30): Promise<Performance[]> => {
    try {
      const response = await clojureClient.get(
        `/api/v1/performance?days=${days}`
      );
      return processResponse<Performance[]>(response);
    } catch (error) {
      console.error("Error fetching performance:", error);
      throw error;
    }
  },

  getPerformanceByAccount: async (
    accountId: string,
    days: number = 30
  ): Promise<Performance[]> => {
    try {
      const response = await clojureClient.get(
        `/api/v1/performance/${accountId}?days=${days}`
      );
      return processResponse<Performance[]>(response);
    } catch (error) {
      console.error("Error fetching account performance:", error);
      throw error;
    }
  },

  // Backtest endpoints
  getBacktests: async (): Promise<BacktestResult[]> => {
    try {
      const response = await clojureClient.get("/api/v1/backtest-ids");
      const backtestIds = processResponse<string[]>(response);

      // Fetch details for each backtest ID
      const backtestPromises = backtestIds.map(async (id) => {
        const detailResponse = await clojureClient.get(
          `/api/v1/backtest/${id}`
        );
        return processResponse<BacktestResult>(detailResponse);
      });

      return Promise.all(backtestPromises);
    } catch (error) {
      console.error("Error fetching backtests:", error);
      throw error;
    }
  },

  getBacktestById: async (id: string): Promise<BacktestDetail> => {
    try {
      const response = await clojureClient.get(`/api/v1/backtest/${id}`);
      return processResponse<BacktestDetail>(response);
    } catch (error) {
      console.error(`Error fetching backtest ${id}:`, error);
      throw error;
    }
  },

  runBacktest: async (
    instruments: string[],
    timeframe: string = "H1"
  ): Promise<string> => {
    try {
      const response = await clojureClient.post("/api/v1/backtest", {
        instruments,
        timeframe,
      });
      const result = processResponse<any>(response);
      return result.id || "";
    } catch (error) {
      console.error("Error running backtest:", error);
      throw error;
    }
  },

  executeTrade: async (
    backtestId: string,
    accountId?: string,
    regularity?: string
  ): Promise<boolean> => {
    try {
      const payload: any = { backtestId };
      if (accountId) payload.accountId = accountId;
      if (regularity) payload.regularity = regularity;

      await clojureClient.post("/api/v1/trade", payload);
      return true;
    } catch (error) {
      console.error(`Error executing trade:`, error);
      throw error;
    }
  },

  stopTrading: async (accountId?: string): Promise<boolean> => {
    try {
      if (accountId) {
        await clojureClient.post("/api/v1/stop-trading", { accountId });
      } else {
        await clojureClient.post("/api/v1/stop-all-trading");
      }
      return true;
    } catch (error) {
      console.error("Error stopping trading:", error);
      throw error;
    }
  },

  closePositions: async (accountId?: string): Promise<boolean> => {
    try {
      if (accountId) {
        await clojureClient.post("/api/v1/close-positions", { accountId });
      } else {
        await clojureClient.post("/api/v1/close-all-positions");
      }
      return true;
    } catch (error) {
      console.error("Error closing positions:", error);
      throw error;
    }
  },

  // Prices endpoints
  getLatestPrice: async (instrument: string): Promise<number> => {
    try {
      const response = await clojureClient.get(`/api/v1/price/${instrument}`);
      const result = processResponse<{ instrument: string; price: number }>(
        response
      );
      return result.price;
    } catch (error) {
      console.error(`Error fetching price for ${instrument}:`, error);
      throw error;
    }
  },

  getLatestPrices: async (
    instruments: string[]
  ): Promise<{ instrument: string; price: number }[]> => {
    try {
      const response = await clojureClient.post("/api/v1/prices", {
        instruments,
      });
      return processResponse<{ instrument: string; price: number }[]>(response);
    } catch (error) {
      console.error("Error fetching prices:", error);
      throw error;
    }
  },

  // Utility endpoints
  collectPerformanceData: async (): Promise<void> => {
    try {
      await clojureClient.post("/api/v1/collect-performance");
    } catch (error) {
      console.error("Error triggering performance data collection:", error);
      throw error;
    }
  },

  getTradeEnvironment: async (): Promise<string> => {
    try {
      const response = await clojureClient.get("/trade-env");
      return processResponse<string>(response);
    } catch (error) {
      console.error("Error fetching trade environment:", error);
      throw error;
    }
  },
};

export default clojureApiService;
