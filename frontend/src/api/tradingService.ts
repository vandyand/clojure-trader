import api from "./apiClient";

// Define interfaces for API responses
export interface Account {
  id: string;
  name: string;
  balance: number;
  currency: string;
  nav: number;
  timestamp: number;
}

export interface Position {
  instrument: string;
  units: number;
  avgPrice: number;
  currentPrice: number;
  pnl: number;
  pnlPercent: number;
  timestamp: number;
}

export interface Performance {
  timestamp: number;
  value: number;
  change: number;
  changePercent: number;
}

export interface BacktestResult {
  id: string;
  instruments: string[];
  startDate: string;
  endDate: string;
  performance: number;
  sharpeRatio: number;
  maxDrawdown: number;
  trades: number;
  winRate: number;
  timeframe: string;
}

export interface BacktestPositionScore {
  instrument: string;
  relBuySellScore: number;
  targetPosition: number;
  latestPrice: number;
  usdBuySellAmount?: number;
}

export interface BacktestDetail extends BacktestResult {
  positionScores: BacktestPositionScore[];
  createdAt: number;
  executedAt: number | null;
}

// Service functions
export const tradingService = {
  // Account endpoints
  getAccounts: () => api.get<Account[]>("/accounts"),
  getAccountById: (id: string) => api.get<Account>(`/accounts/${id}`),
  getAccountsWorth: () =>
    api.get<{
      oanda: number;
      binance: number;
      total: number;
      timestamp: number;
    }>("/accounts/worth"),

  // Position endpoints
  getPositions: () => api.get<Position[]>("/positions"),
  getPositionsByAccount: (accountId: string) =>
    api.get<Position[]>(`/accounts/${accountId}/positions`),

  // Performance endpoints
  getPerformance: (period: string = "all") =>
    api.get<Performance[]>("/performance", { period }),
  getPerformanceByAccount: (accountId: string, period: string = "all") =>
    api.get<Performance[]>(`/accounts/${accountId}/performance`, { period }),

  // Backtest endpoints
  getBacktests: () => api.get<BacktestResult[]>("/backtests"),
  getBacktestById: (id: string) => api.get<BacktestResult>(`/backtests/${id}`),

  // Instrument endpoints
  getInstruments: () => api.get<string[]>("/instruments"),
};

export default tradingService;
