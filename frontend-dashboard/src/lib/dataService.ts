import { supabase } from "./supabase";
import * as oandaApi from "./oanda";

export interface AccountSnapshot {
  timestamp: string;
  accountId: string;
  balance: number;
  unrealizedPL: number;
  nav: number;
  marginUsed: number;
  marginAvailable: number;
  positions: any[];
  environment: "LIVE" | "DEMO";
}

export interface PerformanceData {
  date: string;
  nav: number;
  dailyChange: number;
  dailyChangePercent: number;
}

export async function saveAccountSnapshot(): Promise<boolean> {
  try {
    // Fetch current account data
    const accountSummary = await oandaApi.getAccountSummary();
    const openPositions = await oandaApi.getOpenPositions();

    // Extract relevant data
    const account = accountSummary.account;
    const environment =
      process.env.REACT_APP_OANDA_LIVE_OR_DEMO === "LIVE" ? "LIVE" : "DEMO";

    // Create snapshot object with snake_case keys for Supabase
    const snapshot = {
      timestamp: new Date().toISOString(),
      account_id: account.id,
      balance: parseFloat(account.balance),
      unrealized_pl: parseFloat(account.unrealizedPL),
      nav: parseFloat(account.NAV),
      margin_used: parseFloat(account.marginUsed),
      margin_available: parseFloat(account.marginAvailable),
      positions: openPositions.positions,
      environment: environment as "LIVE" | "DEMO",
    };

    console.log("Saving snapshot to Supabase:", snapshot);

    // Save to Supabase
    const { error } = await supabase.from("account_snapshots").insert(snapshot);

    if (error) {
      console.error("Error saving account snapshot:", error);
      return false;
    }

    console.log("Snapshot saved successfully!");
    return true;
  } catch (error) {
    console.error("Error in saveAccountSnapshot:", error);
    return false;
  }
}

export async function getAccountHistory(days = 30): Promise<AccountSnapshot[]> {
  try {
    const startDate = new Date();
    startDate.setDate(startDate.getDate() - days);

    const { data, error } = await supabase
      .from("account_snapshots")
      .select("*")
      .gte("timestamp", startDate.toISOString())
      .order("timestamp", { ascending: true });

    if (error) {
      console.error("Error fetching account history:", error);
      return [];
    }

    // Convert from snake_case back to camelCase for the frontend
    return (data || []).map((item) => ({
      timestamp: item.timestamp,
      accountId: item.account_id,
      balance: item.balance,
      unrealizedPL: item.unrealized_pl,
      nav: item.nav,
      marginUsed: item.margin_used,
      marginAvailable: item.margin_available,
      positions: item.positions,
      environment: item.environment,
    }));
  } catch (error) {
    console.error("Error in getAccountHistory:", error);
    return [];
  }
}

export async function getDailyPerformance(
  days = 30
): Promise<PerformanceData[]> {
  const snapshots = await getAccountHistory(days);

  if (snapshots.length === 0) {
    return [];
  }

  // Group by day and get last snapshot for each day
  const dailySnapshots = snapshots.reduce(
    (acc: { [key: string]: AccountSnapshot }, snapshot) => {
      const date = snapshot.timestamp.split("T")[0];
      acc[date] = snapshot;
      return acc;
    },
    {}
  );

  // Convert to array of daily performance data
  return Object.values(dailySnapshots).map((snapshot, index, arr) => {
    const prevValue = index > 0 ? arr[index - 1].nav : snapshot.nav;
    const dailyChange = snapshot.nav - prevValue;
    const dailyChangePercent =
      prevValue !== 0 ? (dailyChange / prevValue) * 100 : 0;

    return {
      date: snapshot.timestamp.split("T")[0],
      nav: snapshot.nav,
      dailyChange,
      dailyChangePercent,
    };
  });
}
