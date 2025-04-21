import { supabase } from "./supabase";
import * as oandaApi from "./oanda";
import { DataSource } from "./DataSourceContext";

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

export async function saveAccountSnapshot(
  dataSource: DataSource
): Promise<boolean> {
  try {
    // Fetch current account data
    const accountSummary = await oandaApi.getAccountSummary(dataSource);
    const openPositions = await oandaApi.getOpenPositions(dataSource);

    // Extract relevant data
    const account = accountSummary.account;

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
      environment: dataSource,
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

export async function getAccountHistory(
  days = 30,
  startDateStr?: string,
  endDateStr?: string,
  dataSource?: DataSource
): Promise<AccountSnapshot[]> {
  try {
    let query = supabase.from("account_snapshots").select("*");

    // Filter by data source if provided
    if (dataSource) {
      query = query.eq("environment", dataSource);
    }

    // Use date range if provided, otherwise use days
    if (startDateStr && endDateStr) {
      const startDate = new Date(startDateStr);
      const endDate = new Date(endDateStr);
      // Set end date to end of day to include all data from that day
      endDate.setHours(23, 59, 59, 999);

      query = query
        .gte("timestamp", startDate.toISOString())
        .lte("timestamp", endDate.toISOString());
    } else {
      // Calculate fresh dates using current time
      const endDate = new Date();
      const startDate = new Date();
      startDate.setDate(startDate.getDate() - days);

      // Add milliseconds to ensure we have the most current time
      // This forces reevaluation of the time on each call
      const endTimeIso = new Date(endDate.getTime()).toISOString();
      const startTimeIso = new Date(startDate.getTime()).toISOString();

      console.log("Using date range:", startTimeIso, "to", endTimeIso);

      query = query.gte("timestamp", startTimeIso).lte("timestamp", endTimeIso);
    }

    // Increase the row limit and order by timestamp
    const { data, error } = await query
      .limit(5000) // Fetch up to 5000 rows
      .order("timestamp", { ascending: true });

    if (error) {
      console.error("Error fetching account history:", error);
      return [];
    }

    // Log the timestamps to debug
    console.log("First timestamp:", data?.[0]?.timestamp);
    console.log("Last timestamp:", data?.[data?.length - 1]?.timestamp);
    console.log("Current time:", new Date().toISOString());

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
  days = 30,
  granularity: "daily" | "hourly" = "daily",
  dataSource?: DataSource
): Promise<PerformanceData[]> {
  const snapshots = await getAccountHistory(
    days,
    undefined,
    undefined,
    dataSource
  );
  return processSnapshotsByGranularity(snapshots, granularity);
}

export async function getPerformanceByDateRange(
  startDate: string,
  endDate: string,
  granularity: "daily" | "hourly" = "daily",
  dataSource?: DataSource
): Promise<PerformanceData[]> {
  const snapshots = await getAccountHistory(0, startDate, endDate, dataSource);
  return processSnapshotsByGranularity(snapshots, granularity);
}

function processSnapshotsByGranularity(
  snapshots: AccountSnapshot[],
  granularity: "daily" | "hourly"
): PerformanceData[] {
  if (snapshots.length === 0) {
    return [];
  }

  const getTimeKey = (timestamp: string) => {
    if (granularity === "daily") {
      // Group by day (YYYY-MM-DD)
      return timestamp.split("T")[0];
    } else {
      // Group by hour (YYYY-MM-DDTHH)
      return timestamp.substring(0, 13);
    }
  };

  const formatDate = (key: string) => {
    if (granularity === "daily") {
      // Return as is for daily (already in YYYY-MM-DD format)
      return key;
    } else {
      // Add minutes and seconds for hourly (YYYY-MM-DDTHH:00:00)
      return `${key}:00:00`;
    }
  };

  // Group by selected granularity and get last snapshot for each period
  const groupedSnapshots = snapshots.reduce(
    (acc: { [key: string]: AccountSnapshot }, snapshot) => {
      const timeKey = getTimeKey(snapshot.timestamp);
      acc[timeKey] = snapshot;
      return acc;
    },
    {}
  );

  // Sort keys to ensure chronological order
  const sortedKeys = Object.keys(groupedSnapshots).sort();
  const sortedSnapshots = sortedKeys.map((key) => groupedSnapshots[key]);

  // Convert to array of performance data
  return sortedSnapshots.map((snapshot, index, arr) => {
    const prevValue = index > 0 ? arr[index - 1].nav : snapshot.nav;
    const dailyChange = snapshot.nav - prevValue;
    const dailyChangePercent =
      prevValue !== 0 ? (dailyChange / prevValue) * 100 : 0;

    // Use the timestamp key format based on granularity
    const timeKey = getTimeKey(snapshot.timestamp);

    return {
      date: formatDate(timeKey),
      nav: snapshot.nav,
      dailyChange,
      dailyChangePercent,
    };
  });
}
