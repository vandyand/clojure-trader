import {
  Account,
  Position,
  Performance,
  BacktestResult,
} from "./tradingService";
import { subDays, format } from "date-fns";

// Helper to generate timestamps
const dayToTimestamp = (daysAgo: number) => {
  return subDays(new Date(), daysAgo).getTime();
};

// Helper to create random price variations
const randomChange = (base: number, volatility: number) => {
  return base * (1 + (Math.random() * 2 - 1) * volatility);
};

// Mock Accounts
export const mockAccounts: Account[] = [
  {
    id: "101-001-5729740-001",
    name: "Forex Trading",
    balance: 10250.75,
    currency: "USD",
    nav: 10437.28,
    timestamp: new Date().getTime(),
  },
  {
    id: "101-001-5729740-002",
    name: "Crypto Portfolio",
    balance: 5120.32,
    currency: "USD",
    nav: 5342.18,
    timestamp: new Date().getTime(),
  },
  {
    id: "101-001-5729740-003",
    name: "Automated Strategy 1",
    balance: 3200.15,
    currency: "USD",
    nav: 3187.9,
    timestamp: new Date().getTime(),
  },
];

// Mock Positions
export const mockPositions: Position[] = [
  {
    instrument: "EUR_USD",
    units: 10000,
    avgPrice: 1.08423,
    currentPrice: 1.08673,
    pnl: 25.0,
    pnlPercent: 0.23,
    timestamp: new Date().getTime(),
  },
  {
    instrument: "GBP_USD",
    units: -5000,
    avgPrice: 1.24532,
    currentPrice: 1.24217,
    pnl: 15.75,
    pnlPercent: 0.25,
    timestamp: new Date().getTime(),
  },
  {
    instrument: "USD_JPY",
    units: 20000,
    avgPrice: 151.25,
    currentPrice: 151.87,
    pnl: 41.18,
    pnlPercent: 0.41,
    timestamp: new Date().getTime(),
  },
  {
    instrument: "BTC_USD",
    units: 0.1,
    avgPrice: 68234.5,
    currentPrice: 67921.25,
    pnl: -31.33,
    pnlPercent: -0.46,
    timestamp: new Date().getTime(),
  },
  {
    instrument: "ETH_USD",
    units: 1.5,
    avgPrice: 3245.78,
    currentPrice: 3301.45,
    pnl: 83.5,
    pnlPercent: 1.71,
    timestamp: new Date().getTime(),
  },
];

// Mock Performance data (90 days)
export const mockPerformance: Performance[] = (() => {
  const performanceData: Performance[] = [];
  const baseValue = 10000; // Starting account value

  for (let i = 0; i < 90; i++) {
    const dailyChange = Math.random() * 0.01 * (Math.random() > 0.4 ? 1 : -1); // Daily fluctuation
    const prevValue =
      i === 0 ? baseValue : performanceData[i - 1]?.value || baseValue;
    const value = prevValue * (1 + dailyChange);

    performanceData.push({
      timestamp: dayToTimestamp(90 - i),
      value: parseFloat(value.toFixed(2)),
      change: parseFloat((value - prevValue).toFixed(2)),
      changePercent: parseFloat((dailyChange * 100).toFixed(2)),
    });
  }

  return performanceData.reverse();
})();

// Mock Backtests
export const mockBacktests: BacktestResult[] = [
  {
    id: "bt-001",
    instruments: ["EUR_USD", "GBP_USD", "USD_JPY", "AUD_USD"],
    startDate: format(subDays(new Date(), 180), "yyyy-MM-dd"),
    endDate: format(subDays(new Date(), 30), "yyyy-MM-dd"),
    performance: 8.72,
    sharpeRatio: 1.23,
    maxDrawdown: 3.17,
    trades: 142,
    winRate: 58.45,
    timeframe: "H1",
  },
  {
    id: "bt-002",
    instruments: ["BTC_USD", "ETH_USD", "SOL_USD"],
    startDate: format(subDays(new Date(), 120), "yyyy-MM-dd"),
    endDate: format(subDays(new Date(), 30), "yyyy-MM-dd"),
    performance: 15.63,
    sharpeRatio: 1.47,
    maxDrawdown: 9.21,
    trades: 85,
    winRate: 61.18,
    timeframe: "H4",
  },
  {
    id: "bt-003",
    instruments: ["USD_CAD", "NZD_USD", "EUR_GBP"],
    startDate: format(subDays(new Date(), 90), "yyyy-MM-dd"),
    endDate: format(subDays(new Date(), 14), "yyyy-MM-dd"),
    performance: 4.31,
    sharpeRatio: 0.93,
    maxDrawdown: 2.46,
    trades: 76,
    winRate: 51.32,
    timeframe: "H1",
  },
];

// Mock Instruments
export const mockInstruments = [
  "EUR_USD",
  "GBP_USD",
  "USD_JPY",
  "AUD_USD",
  "USD_CAD",
  "USD_CHF",
  "NZD_USD",
  "EUR_JPY",
  "GBP_JPY",
  "EUR_GBP",
  "BTC_USD",
  "ETH_USD",
  "SOL_USD",
  "XRP_USD",
  "ADA_USD",
];

// Mock API methods
export const mockApiService = {
  getAccounts: () => Promise.resolve(mockAccounts),
  getAccountById: (id: string) =>
    Promise.resolve(
      mockAccounts.find((acc) => acc.id === id) || mockAccounts[0]
    ),
  getAccountsWorth: () =>
    Promise.resolve({
      oanda: 16825.33,
      binance: 5342.18,
      total: 22167.51,
      timestamp: new Date().getTime(),
    }),

  getPositions: () => Promise.resolve(mockPositions),
  getPositionsByAccount: (accountId: string) => {
    // Filter positions to simulate different accounts
    if (accountId === "101-001-5729740-001") {
      return Promise.resolve(mockPositions.slice(0, 3));
    } else if (accountId === "101-001-5729740-002") {
      return Promise.resolve(mockPositions.slice(3, 5));
    }
    return Promise.resolve([]);
  },

  getPerformance: () => Promise.resolve(mockPerformance),
  getPerformanceByAccount: (accountId: string) => {
    // Simulate different account performances
    const modifier =
      accountId === "101-001-5729740-001"
        ? 1.05
        : accountId === "101-001-5729740-002"
        ? 1.12
        : 0.97;

    return Promise.resolve(
      mockPerformance.map((p) => ({
        ...p,
        value: parseFloat((p.value * modifier).toFixed(2)),
        change: parseFloat((p.change * modifier).toFixed(2)),
      }))
    );
  },

  getBacktests: () => Promise.resolve(mockBacktests),
  getBacktestById: (id: string) =>
    Promise.resolve(
      mockBacktests.find((bt) => bt.id === id) || mockBacktests[0]
    ),

  getInstruments: () => Promise.resolve(mockInstruments),
};
