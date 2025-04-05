import axios from "axios";
import {
  Account,
  Position,
  Performance,
  BacktestResult,
  BacktestDetail,
  BacktestPositionScore,
} from "./tradingService";
import {
  storeAccountSnapshot,
  storePositionSnapshot,
  getAccountPerformance,
} from "../utils/timeSeriesStorage";
import { format, subDays } from "date-fns";

// Constants
const OANDA_API_URL =
  process.env.REACT_APP_OANDA_API_URL || "https://api-fxpractice.oanda.com/v3/";
const OANDA_ACCOUNT_ID =
  process.env.REACT_APP_OANDA_ACCOUNT_ID || "101-001-5729740-001";

// Create axios instance with default config
const oandaClient = axios.create({
  baseURL: OANDA_API_URL,
  headers: {
    "Content-Type": "application/json",
    Authorization: `Bearer ${process.env.REACT_APP_OANDA_API_KEY || ""}`,
  },
});

// Type definitions for OANDA API responses
interface OandaAccount {
  id: string;
  alias: string;
  currency: string;
  balance: string;
  createdByUserID: number;
  createdTime: string;
  pl: string;
  resettablePL: string;
  marginRate: string;
  marginCallMarginUsed: string;
  marginCallPercent: string;
  openTradeCount: number;
  openPositionCount: number;
  pendingOrderCount: number;
  hedgingEnabled: boolean;
  unrealizedPL: string;
  NAV: string;
  marginUsed: string;
  marginAvailable: string;
  positionValue: string;
  marginCloseoutUnrealizedPL: string;
  marginCloseoutNAV: string;
  marginCloseoutMarginUsed: string;
  marginCloseoutPercent: string;
  withdrawalLimit: string;
  marginCallEnterTime: string;
  marginCallExtensionCount: number;
  lastMarginCallExtensionTime: string;
  lastTransactionID: string;
}

interface OandaPosition {
  instrument: string;
  pl: string;
  unrealizedPL: string;
  marginUsed: string;
  resettablePL: string;
  financing: string;
  commission: string;
  guaranteedExecutionFees: string;
  long: {
    units: string;
    averagePrice: string;
    tradeIDs: string[];
    pl: string;
    unrealizedPL: string;
    resettablePL: string;
    financing: string;
  };
  short: {
    units: string;
    averagePrice: string;
    tradeIDs: string[];
    pl: string;
    unrealizedPL: string;
    resettablePL: string;
    financing: string;
  };
}

interface OandaPricing {
  type: string;
  time: string;
  bids: Array<{ price: string; liquidity: number }>;
  asks: Array<{ price: string; liquidity: number }>;
  closeoutBid: string;
  closeoutAsk: string;
  status: string;
  tradeable: boolean;
  instrument: string;
}

// Mapper functions to transform OANDA response to our app's format
const mapOandaAccount = (oandaAccount: OandaAccount): Account => ({
  id: oandaAccount.id,
  name: oandaAccount.alias || `Account ${oandaAccount.id}`,
  balance: parseFloat(oandaAccount.balance),
  currency: oandaAccount.currency,
  nav: parseFloat(oandaAccount.NAV),
  timestamp: Date.now(),
});

const mapOandaPosition = (
  position: OandaPosition,
  pricing?: OandaPricing
): Position => {
  // Extract position data
  const longUnits = parseInt(position.long?.units || "0");
  const shortUnits = parseInt(position.short?.units || "0");
  const units = longUnits + shortUnits; // One will be 0 or negative

  // Determine which side to use for average price
  const isLong = units > 0;
  const avgPrice = parseFloat(
    isLong ? position.long?.averagePrice : position.short?.averagePrice
  );

  // Current price from pricing data if available, otherwise use avg price as fallback
  const currentPrice = pricing
    ? parseFloat(isLong ? pricing.asks[0].price : pricing.bids[0].price)
    : avgPrice;

  // Calculate PnL
  const pnl = parseFloat(position.unrealizedPL);
  const pnlPercent = avgPrice ? (pnl / (Math.abs(units) * avgPrice)) * 100 : 0;

  return {
    instrument: position.instrument,
    units,
    avgPrice,
    currentPrice,
    pnl,
    pnlPercent,
    timestamp: Date.now(),
  };
};

// Service functions
export const oandaApiService = {
  getAccounts: async (): Promise<Account[]> => {
    try {
      // If we have a predefined account ID, we'll use that directly
      if (OANDA_ACCOUNT_ID) {
        const accountResponse = await oandaClient.get(
          `/accounts/${OANDA_ACCOUNT_ID}`
        );
        const account = mapOandaAccount(accountResponse.data.account);

        // Store account snapshot for historical tracking
        storeAccountSnapshot(account);

        return [account];
      }

      // Otherwise, fetch all accounts
      const response = await oandaClient.get("/accounts");
      const accounts = response.data.accounts.map(
        (accSummary: { id: string }) => accSummary.id
      );

      // Fetch full details for each account
      const accountPromises = accounts.map(async (id: string) => {
        const accountResponse = await oandaClient.get(`/accounts/${id}`);
        const account = mapOandaAccount(accountResponse.data.account);

        // Store account snapshot for historical tracking
        storeAccountSnapshot(account);

        return account;
      });

      return Promise.all(accountPromises);
    } catch (error) {
      console.error("Error fetching OANDA accounts:", error);
      throw error;
    }
  },

  getAccountById: async (id: string): Promise<Account> => {
    try {
      const response = await oandaClient.get(`/accounts/${id}`);
      return mapOandaAccount(response.data.account);
    } catch (error) {
      console.error(`Error fetching OANDA account ${id}:`, error);
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
      const accounts = await oandaApiService.getAccounts();
      const oandaTotal = accounts.reduce(
        (sum, account) => sum + account.nav,
        0
      );

      return {
        oanda: oandaTotal,
        binance: 0, // Real Binance integration would go here
        total: oandaTotal,
        timestamp: Date.now(),
      };
    } catch (error) {
      console.error("Error calculating accounts worth:", error);
      throw error;
    }
  },

  getPositions: async (): Promise<Position[]> => {
    try {
      const accounts = await oandaApiService.getAccounts();
      const positionPromises = accounts.map((account) =>
        oandaApiService.getPositionsByAccount(account.id)
      );

      const positionArrays = await Promise.all(positionPromises);
      return positionArrays.flat();
    } catch (error) {
      console.error("Error fetching all positions:", error);
      throw error;
    }
  },

  getPositionsByAccount: async (accountId: string): Promise<Position[]> => {
    try {
      const response = await oandaClient.get(
        `/accounts/${accountId}/openPositions`
      );
      const positions = response.data.positions;

      // Get current prices for each instrument
      const instruments = positions.map((pos: OandaPosition) => pos.instrument);
      const pricingResponse = await oandaClient.get(
        `/accounts/${accountId}/pricing`,
        { params: { instruments: instruments.join(",") } }
      );

      const pricingMap = pricingResponse.data.prices.reduce(
        (map: Record<string, OandaPricing>, price: OandaPricing) => {
          map[price.instrument] = price;
          return map;
        },
        {}
      );

      const mappedPositions = positions.map((pos: OandaPosition) =>
        mapOandaPosition(pos, pricingMap[pos.instrument])
      );

      // Store position snapshots for historical tracking
      mappedPositions.forEach((position: Position) =>
        storePositionSnapshot(position)
      );

      return mappedPositions;
    } catch (error) {
      console.error(
        `Error fetching positions for account ${accountId}:`,
        error
      );
      throw error;
    }
  },

  getPerformance: async (): Promise<Performance[]> => {
    try {
      // Use the stored performance data from our time series storage
      if (OANDA_ACCOUNT_ID) {
        const performanceData = getAccountPerformance(OANDA_ACCOUNT_ID);

        // If we have stored performance data, return it
        if (performanceData.length > 0) {
          return performanceData;
        }
      }

      // If we don't have any data yet, fetch the current account and return a single point
      const accounts = await oandaApiService.getAccounts();
      if (accounts.length > 0) {
        const account = accounts[0];
        return [
          {
            timestamp: Date.now(),
            value: account.nav,
            change: 0,
            changePercent: 0,
          },
        ];
      }

      // Fallback to empty array if no accounts
      return [];
    } catch (error) {
      console.error("Error getting performance data:", error);
      return [];
    }
  },

  getPerformanceByAccount: async (
    accountId: string
  ): Promise<Performance[]> => {
    try {
      // Use the stored performance data from our time series storage
      const performanceData = getAccountPerformance(accountId);

      // If we have stored performance data, return it
      if (performanceData.length > 0) {
        return performanceData;
      }

      // If we don't have any data yet, fetch the current account and return a single point
      const account = await oandaApiService.getAccountById(accountId);
      return [
        {
          timestamp: Date.now(),
          value: account.nav,
          change: 0,
          changePercent: 0,
        },
      ];
    } catch (error) {
      console.error(
        `Error getting performance data for account ${accountId}:`,
        error
      );
      return [];
    }
  },

  getInstruments: async (): Promise<string[]> => {
    try {
      // Use predefined account ID if available
      let accountId = OANDA_ACCOUNT_ID;

      if (!accountId) {
        const response = await oandaClient.get("/accounts");
        accountId = response.data.accounts[0]?.id;

        if (!accountId) {
          throw new Error("No accounts found");
        }
      }

      const instrumentsResponse = await oandaClient.get(
        `/accounts/${accountId}/instruments`
      );

      return instrumentsResponse.data.instruments.map(
        (instrument: { name: string }) => instrument.name
      );
    } catch (error) {
      console.error("Error fetching instruments:", error);
      throw error;
    }
  },

  // Backtests methods
  getBacktests: async (): Promise<BacktestResult[]> => {
    try {
      // Mock data for now - in a real implementation, we would fetch this from the Clojure backend
      // To be replaced with actual API calls to the Clojure backend
      const mockBacktests: BacktestResult[] = [
        {
          id: "bt-001",
          instruments: ["EUR_USD", "GBP_USD", "USD_JPY"],
          startDate: format(subDays(new Date(), 30), "yyyy-MM-dd"),
          endDate: format(new Date(), "yyyy-MM-dd"),
          performance: 3.45,
          sharpeRatio: 1.2,
          maxDrawdown: 1.8,
          trades: 42,
          winRate: 58.3,
          timeframe: "H1",
        },
        {
          id: "bt-002",
          instruments: ["AUD_USD", "NZD_USD", "USD_CAD"],
          startDate: format(subDays(new Date(), 15), "yyyy-MM-dd"),
          endDate: format(new Date(), "yyyy-MM-dd"),
          performance: 1.87,
          sharpeRatio: 0.95,
          maxDrawdown: 1.2,
          trades: 28,
          winRate: 53.6,
          timeframe: "H4",
        },
      ];

      return mockBacktests;
    } catch (error) {
      console.error("Error fetching backtests:", error);
      throw error;
    }
  },

  getBacktestById: async (id: string): Promise<BacktestDetail> => {
    try {
      // Mock data for now - in a real implementation, we would fetch this from the Clojure backend
      // This would be replaced with actual API calls
      const mockBacktestDetail: BacktestDetail = {
        id,
        instruments: ["EUR_USD", "GBP_USD", "USD_JPY", "AUD_USD"],
        startDate: format(subDays(new Date(), 30), "yyyy-MM-dd"),
        endDate: format(new Date(), "yyyy-MM-dd"),
        performance: 3.45,
        sharpeRatio: 1.2,
        maxDrawdown: 1.8,
        trades: 42,
        winRate: 58.3,
        timeframe: "H1",
        createdAt: subDays(new Date(), 1).getTime(),
        executedAt: new Date().getTime(),
        positionScores: [
          {
            instrument: "EUR_USD",
            relBuySellScore: 0.75,
            targetPosition: 10000,
            latestPrice: 1.08673,
            usdBuySellAmount: 8673.0,
          },
          {
            instrument: "GBP_USD",
            relBuySellScore: -0.32,
            targetPosition: -5000,
            latestPrice: 1.24217,
            usdBuySellAmount: -6210.85,
          },
          {
            instrument: "USD_JPY",
            relBuySellScore: 0.54,
            targetPosition: 20000,
            latestPrice: 151.87,
            usdBuySellAmount: 13179.85,
          },
          {
            instrument: "AUD_USD",
            relBuySellScore: 0.12,
            targetPosition: 2500,
            latestPrice: 0.6547,
            usdBuySellAmount: 1636.75,
          },
        ],
      };

      return mockBacktestDetail;
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
      // Mock response - in a real implementation, this would trigger the backtest on the Clojure backend
      // and return a backtest ID to track status
      return `bt-${Date.now().toString().substring(8)}`;
    } catch (error) {
      console.error("Error running backtest:", error);
      throw error;
    }
  },

  executeBacktestPositions: async (
    backtestId: string,
    amount: number
  ): Promise<boolean> => {
    try {
      // Mock response - in a real implementation, this would call the Clojure backend to execute
      // the positions from the backtest result
      console.log(`Executing backtest ${backtestId} with amount $${amount}`);
      return true;
    } catch (error) {
      console.error(`Error executing backtest ${backtestId}:`, error);
      throw error;
    }
  },
};

export default oandaApiService;
