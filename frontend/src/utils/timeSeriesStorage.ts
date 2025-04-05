import { Account, Position, Performance } from "../api/tradingService";

/**
 * Time Series Storage
 *
 * Handles persistent storage of time series data for accounts and positions
 * Uses localStorage to maintain data between sessions
 */

// Storage keys
const ACCOUNT_HISTORY_KEY = "clojure_trader_account_history";
const POSITION_HISTORY_KEY = "clojure_trader_position_history";

// Maximum number of data points to store (90 days)
const MAX_DATA_POINTS = 90;

// Interfaces for stored data
interface StoredAccountSnapshot {
  timestamp: number;
  accountId: string;
  balance: number;
  nav: number;
}

interface StoredPositionSnapshot {
  timestamp: number;
  instrument: string;
  avgPrice: number;
  currentPrice: number;
  pnl: number;
  pnlPercent: number;
}

/**
 * Store a snapshot of account data
 */
export const storeAccountSnapshot = (account: Account): void => {
  try {
    // Get existing data
    const existingDataStr = localStorage.getItem(ACCOUNT_HISTORY_KEY) || "{}";
    const existingData: Record<string, StoredAccountSnapshot[]> =
      JSON.parse(existingDataStr);

    // Initialize array for this account if it doesn't exist
    if (!existingData[account.id]) {
      existingData[account.id] = [];
    }

    // Only store one snapshot per day
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const todayTimestamp = today.getTime();

    // Check if we already have a snapshot for today
    const todayExists = existingData[account.id].some((snapshot) => {
      const snapshotDate = new Date(snapshot.timestamp);
      snapshotDate.setHours(0, 0, 0, 0);
      return snapshotDate.getTime() === todayTimestamp;
    });

    // If we don't have a snapshot for today, add one
    if (!todayExists) {
      existingData[account.id].push({
        timestamp: Date.now(),
        accountId: account.id,
        balance: account.balance,
        nav: account.nav,
      });

      // Trim to max data points
      if (existingData[account.id].length > MAX_DATA_POINTS) {
        existingData[account.id] = existingData[account.id].slice(
          -MAX_DATA_POINTS
        );
      }

      // Save back to localStorage
      localStorage.setItem(ACCOUNT_HISTORY_KEY, JSON.stringify(existingData));
    }
  } catch (error) {
    console.error("Error storing account snapshot:", error);
  }
};

/**
 * Store snapshots for multiple accounts
 */
export const storeAccountSnapshots = (accounts: Account[]): void => {
  accounts.forEach((account) => storeAccountSnapshot(account));
};

/**
 * Store a snapshot of position data
 */
export const storePositionSnapshot = (position: Position): void => {
  try {
    // Get existing data
    const existingDataStr = localStorage.getItem(POSITION_HISTORY_KEY) || "{}";
    const existingData: Record<string, StoredPositionSnapshot[]> =
      JSON.parse(existingDataStr);

    // Initialize array for this instrument if it doesn't exist
    if (!existingData[position.instrument]) {
      existingData[position.instrument] = [];
    }

    // Only store one snapshot per day
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const todayTimestamp = today.getTime();

    // Check if we already have a snapshot for today
    const todayExists = existingData[position.instrument].some((snapshot) => {
      const snapshotDate = new Date(snapshot.timestamp);
      snapshotDate.setHours(0, 0, 0, 0);
      return snapshotDate.getTime() === todayTimestamp;
    });

    // If we don't have a snapshot for today, add one
    if (!todayExists) {
      existingData[position.instrument].push({
        timestamp: Date.now(),
        instrument: position.instrument,
        avgPrice: position.avgPrice,
        currentPrice: position.currentPrice,
        pnl: position.pnl,
        pnlPercent: position.pnlPercent,
      });

      // Trim to max data points
      if (existingData[position.instrument].length > MAX_DATA_POINTS) {
        existingData[position.instrument] = existingData[
          position.instrument
        ].slice(-MAX_DATA_POINTS);
      }

      // Save back to localStorage
      localStorage.setItem(POSITION_HISTORY_KEY, JSON.stringify(existingData));
    }
  } catch (error) {
    console.error("Error storing position snapshot:", error);
  }
};

/**
 * Store snapshots for multiple positions
 */
export const storePositionSnapshots = (positions: Position[]): void => {
  positions.forEach((position) => storePositionSnapshot(position));
};

/**
 * Get account performance data for a specific account
 */
export const getAccountPerformance = (accountId: string): Performance[] => {
  try {
    const existingDataStr = localStorage.getItem(ACCOUNT_HISTORY_KEY) || "{}";
    const existingData: Record<string, StoredAccountSnapshot[]> =
      JSON.parse(existingDataStr);

    if (!existingData[accountId] || existingData[accountId].length === 0) {
      return [];
    }

    // Sort by timestamp
    const sortedSnapshots = [...existingData[accountId]].sort(
      (a, b) => a.timestamp - b.timestamp
    );

    // Convert to Performance objects
    return sortedSnapshots.map((snapshot, index) => {
      const prevSnapshot = index > 0 ? sortedSnapshots[index - 1] : null;
      const change = prevSnapshot ? snapshot.nav - prevSnapshot.nav : 0;
      const changePercent = prevSnapshot
        ? (change / prevSnapshot.nav) * 100
        : 0;

      return {
        timestamp: snapshot.timestamp,
        value: snapshot.nav,
        change,
        changePercent,
      };
    });
  } catch (error) {
    console.error("Error getting account performance:", error);
    return [];
  }
};

/**
 * Get position performance data for specified positions and time period
 * Returns normalized values where each position starts at 1.0
 */
export const getPositionPerformance = (
  instruments: string[],
  startTimestamp: number = 0
): Record<string, { timestamp: number; normalizedValue: number }[]> => {
  try {
    const existingDataStr = localStorage.getItem(POSITION_HISTORY_KEY) || "{}";
    const existingData: Record<string, StoredPositionSnapshot[]> =
      JSON.parse(existingDataStr);

    const result: Record<
      string,
      { timestamp: number; normalizedValue: number }[]
    > = {};

    instruments.forEach((instrument) => {
      if (!existingData[instrument] || existingData[instrument].length === 0) {
        result[instrument] = [];
        return;
      }

      // Filter by start timestamp and sort
      const filteredSnapshots = existingData[instrument]
        .filter((snapshot) => snapshot.timestamp >= startTimestamp)
        .sort((a, b) => a.timestamp - b.timestamp);

      if (filteredSnapshots.length === 0) {
        result[instrument] = [];
        return;
      }

      // Get baseline price for normalization
      const baselinePrice = filteredSnapshots[0].currentPrice;

      // Calculate normalized values
      result[instrument] = filteredSnapshots.map((snapshot) => ({
        timestamp: snapshot.timestamp,
        normalizedValue: snapshot.currentPrice / baselinePrice,
      }));
    });

    return result;
  } catch (error) {
    console.error("Error getting position performance:", error);
    return {};
  }
};

/**
 * Clear all stored time series data
 */
export const clearTimeSeriesData = (): void => {
  localStorage.removeItem(ACCOUNT_HISTORY_KEY);
  localStorage.removeItem(POSITION_HISTORY_KEY);
};
