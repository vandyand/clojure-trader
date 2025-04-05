import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  ReactNode,
} from "react";
import { mockApiService } from "../api/mockData";
import oandaApiService from "../api/oandaApiClient";
import { Account, Position, Performance } from "../api/tradingService";

// Define API source type
type ApiSource = "mock" | "oanda";

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
  // Actions
  setSelectedAccountId: (id: string | null) => void;
  refreshData: () => void;
  setApiSource: (source: ApiSource) => void;
}

// Create the context with default values
const TradingContext = createContext<TradingContextState>({
  accounts: [],
  positions: [],
  performance: [],
  accountsWorth: null,
  selectedAccountId: null,
  isLoading: false,
  error: null,
  apiSource: "mock", // Default to mock data
  setSelectedAccountId: () => {},
  refreshData: () => {},
  setApiSource: () => {},
});

// Custom hook to use the context
export const useTradingContext = () => useContext(TradingContext);

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
  const apiService = apiSource === "mock" ? mockApiService : oandaApiService;

  // Function to fetch all data
  const fetchData = async () => {
    setIsLoading(true);
    setError(null);

    try {
      // Use the selected API service (mock or OANDA)
      const accountsData = await apiService.getAccounts();
      const positionsData = await apiService.getPositions();
      let performanceData: Performance[] = [];

      // For performance data, if using OANDA and we get empty array, fall back to mock
      performanceData = await apiService.getPerformance();
      if (apiSource === "oanda" && performanceData.length === 0) {
        performanceData = await mockApiService.getPerformance();
      }

      const accountsWorthData = await apiService.getAccountsWorth();

      setAccounts(accountsData);
      setPositions(positionsData);
      setPerformance(performanceData);
      setAccountsWorth(accountsWorthData);

      // Set default selected account if not already set
      if (!selectedAccountId && accountsData.length > 0) {
        setSelectedAccountId(accountsData[0].id);
      }
    } catch (err) {
      setError(
        `Failed to fetch trading data from ${apiSource}. Please try again later.`
      );
      console.error(err);

      // If OANDA API fails, fall back to mock data
      if (apiSource === "oanda") {
        try {
          const accountsData = await mockApiService.getAccounts();
          const positionsData = await mockApiService.getPositions();
          const performanceData = await mockApiService.getPerformance();
          const accountsWorthData = await mockApiService.getAccountsWorth();

          setAccounts(accountsData);
          setPositions(positionsData);
          setPerformance(performanceData);
          setAccountsWorth(accountsWorthData);

          setError(
            `Using mock data instead of OANDA API due to connection error.`
          );
        } catch (fallbackErr) {
          console.error("Even fallback to mock data failed:", fallbackErr);
        }
      }
    } finally {
      setIsLoading(false);
    }
  };

  // Effect to fetch data when API source changes
  useEffect(() => {
    fetchData();

    // Optional: Set up polling for real-time updates
    const pollingInterval = setInterval(() => {
      fetchData();
    }, 60000); // Poll every minute

    return () => clearInterval(pollingInterval);
  }, [apiSource]); // Refresh when API source changes

  // Fetch positions when selected account changes
  useEffect(() => {
    if (selectedAccountId) {
      const fetchPositions = async () => {
        setIsLoading(true);
        try {
          const positionsData = await apiService.getPositionsByAccount(
            selectedAccountId
          );
          setPositions(positionsData);
        } catch (err) {
          console.error(err);
          if (apiSource === "oanda") {
            try {
              // Fallback to mock data if OANDA API fails
              const positionsData = await mockApiService.getPositionsByAccount(
                selectedAccountId
              );
              setPositions(positionsData);
            } catch (fallbackErr) {
              console.error("Fallback positions fetch failed:", fallbackErr);
            }
          }
        } finally {
          setIsLoading(false);
        }
      };

      fetchPositions();
    }
  }, [selectedAccountId, apiSource]);

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
    setSelectedAccountId,
    refreshData: fetchData,
    setApiSource,
  };

  return (
    <TradingContext.Provider value={contextValue}>
      {children}
    </TradingContext.Provider>
  );
};

export default TradingContext;
