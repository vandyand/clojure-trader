import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  ReactNode,
} from "react";
import { mockApiService } from "../api/mockData";
import oandaApiService from "../api/oandaApiClient";
import clojureApiService from "../api/clojureApiClient";
import { Account, Position, Performance } from "../api/tradingService";

// Define API source type
type ApiSource = "mock" | "oanda" | "clojure";

// Define the context state interface
interface TradingContextState {
  accounts: Account[];
  positions: Position[];
  performance: Performance[];
  accountsWorth: {
    oanda: number;
    binance: number;
    total: number;
    timestamp: number;
  } | null;
  selectedAccountId: string | null;
  isLoading: boolean;
  error: string | null;
  apiSource: ApiSource;
  fetchAccounts: () => Promise<void>;
  fetchPositions: (accountId?: string) => Promise<void>;
  fetchPerformance: (days?: number) => Promise<void>;
  refreshData: () => Promise<void>;
  setApiSource: (source: ApiSource) => void;
  setSelectedAccountId: (id: string | null) => void;
}

// Create the context with default values
const TradingContext = createContext<TradingContextState | undefined>(
  undefined
);

// Custom hook to use the context
export const useTradingContext = () => {
  const context = useContext(TradingContext);
  if (context === undefined) {
    throw new Error("useTradingContext must be used within a TradingProvider");
  }
  return context;
};

// Provider component
interface TradingProviderProps {
  children: ReactNode;
}

export const TradingProvider: React.FC<TradingProviderProps> = ({
  children,
}) => {
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [positions, setPositions] = useState<Position[]>([]);
  const [performance, setPerformance] = useState<Performance[]>([]);
  const [accountsWorth, setAccountsWorth] =
    useState<TradingContextState["accountsWorth"]>(null);
  const [selectedAccountId, setSelectedAccountId] = useState<string | null>(
    null
  );
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Use environment variable for default, fallback to "mock" if not set
  const defaultApiSource =
    (process.env.REACT_APP_DEFAULT_API_SOURCE as ApiSource) || "mock";
  const [apiSource, setApiSource] = useState<ApiSource>(defaultApiSource);

  // Select the appropriate API service based on the source
  const getApiService = () => {
    switch (apiSource) {
      case "mock":
        return mockApiService;
      case "oanda":
        return oandaApiService;
      case "clojure":
        return clojureApiService;
      default:
        return mockApiService;
    }
  };

  // Fetch accounts data
  const fetchAccounts = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const apiService = getApiService();
      const fetchedAccounts = await apiService.getAccounts();
      setAccounts(fetchedAccounts);

      // If there are accounts and no selectedAccountId yet, set the first one
      if (fetchedAccounts.length > 0 && !selectedAccountId) {
        setSelectedAccountId(fetchedAccounts[0].id);
      }

      // Fetch accounts worth data if available
      try {
        if (apiService.getAccountsWorth) {
          const worth = await apiService.getAccountsWorth();
          setAccountsWorth(worth);
        }
      } catch (err) {
        console.error("Error fetching accounts worth:", err);
        // Don't set error state for worth as it's secondary
      }
    } catch (err) {
      setError("Failed to fetch accounts data");
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  // Fetch positions data
  const fetchPositions = async (accountId?: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const apiService = getApiService();
      let fetchedPositions;

      if (accountId) {
        fetchedPositions = await apiService.getPositionsByAccount(accountId);
      } else if (selectedAccountId) {
        fetchedPositions = await apiService.getPositionsByAccount(
          selectedAccountId
        );
      } else {
        fetchedPositions = await apiService.getPositions();
      }

      setPositions(fetchedPositions);
    } catch (err) {
      setError("Failed to fetch positions data");
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  // Fetch performance data
  const fetchPerformance = async (days: number = 30) => {
    setIsLoading(true);
    setError(null);
    try {
      const apiService = getApiService();
      let fetchedPerformance;

      if (selectedAccountId) {
        fetchedPerformance = await apiService.getPerformanceByAccount(
          selectedAccountId,
          days
        );
      } else {
        fetchedPerformance = await apiService.getPerformance(days);
      }

      setPerformance(fetchedPerformance);
    } catch (err) {
      setError("Failed to fetch performance data");
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  // Initial data load
  useEffect(() => {
    fetchAccounts();
  }, [apiSource]);

  // Fetch position data when selectedAccountId changes
  useEffect(() => {
    if (selectedAccountId) {
      fetchPositions(selectedAccountId);
      fetchPerformance();
    }
  }, [selectedAccountId]);

  // Provide the context value
  const contextValue: TradingContextState = {
    accounts,
    positions,
    performance,
    accountsWorth,
    selectedAccountId,
    isLoading,
    error,
    apiSource,
    fetchAccounts,
    fetchPositions,
    fetchPerformance,
    refreshData: async () => {
      await fetchAccounts();
      await fetchPositions();
      await fetchPerformance();
    },
    setApiSource,
    setSelectedAccountId,
  };

  return (
    <TradingContext.Provider value={contextValue}>
      {children}
    </TradingContext.Provider>
  );
};

export default TradingContext;
