import { supabase } from "./supabase";
import * as oandaApi from "./oanda";
import { DataSource } from "./DataSourceContext";
import { getSnapshotsFromDB, saveSnapshotsToDB } from "./db"; // Import DB functions

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
    let requestedStartTimeISO: string;
    let requestedEndTimeISO: string;
    const currentEnvironment = dataSource || "DEMO"; // Default to DEMO if not specified

    // Determine the full requested date range
    if (startDateStr && endDateStr) {
      const startDate = new Date(startDateStr);
      const endDate = new Date(endDateStr);
      endDate.setHours(23, 59, 59, 999);
      requestedStartTimeISO = startDate.toISOString();
      requestedEndTimeISO = endDate.toISOString();
    } else {
      const endDate = new Date();
      const startDate = new Date();
      startDate.setDate(startDate.getDate() - days);
      requestedStartTimeISO = startDate.toISOString();
      requestedEndTimeISO = endDate.toISOString();
    }

    // 1. Fetch existing data from IndexedDB for the requested range
    const { snapshots: cachedSnapshots, latestTimestamp: latestTimestampInDB } =
      await getSnapshotsFromDB(
        requestedStartTimeISO,
        requestedEndTimeISO,
        currentEnvironment
      );

    // 2. Determine the start time for the Supabase fetch
    let fetchStartTimeISO = requestedStartTimeISO; // Default to fetching the whole range
    if (latestTimestampInDB) {
      const fetchStartDate = new Date(latestTimestampInDB);
      // Add 1ms to avoid fetching the last cached record again
      fetchStartDate.setMilliseconds(fetchStartDate.getMilliseconds() + 1);
      // Only adjust fetch start time if it's later than the initially requested start time
      if (fetchStartDate.toISOString() > requestedStartTimeISO) {
        fetchStartTimeISO = fetchStartDate.toISOString();
      }
      console.log(
        `[Data Service] Latest cache timestamp: ${latestTimestampInDB}. Fetching from: ${fetchStartTimeISO}`
      );
    } else {
      console.log(
        "[Data Service] No cache found. Fetching full range from Supabase."
      );
    }

    let newlyFetchedSnapshots: AccountSnapshot[] = [];

    // 3. Fetch from Supabase only if the fetch start time is before the requested end time
    if (fetchStartTimeISO < requestedEndTimeISO) {
      console.log(
        `[Data Service] Fetching from Supabase from ${fetchStartTimeISO} to ${requestedEndTimeISO}...`
      );
      let query = supabase.from("account_snapshots").select("*");

      if (dataSource) {
        query = query.eq("environment", dataSource);
      }

      // Fetch data from the calculated start time to the requested end time
      query = query
        .gte("timestamp", fetchStartTimeISO)
        .lte("timestamp", requestedEndTimeISO);

      const { data, error } = await query
        .limit(10000) // Keep the increased limit
        .order("timestamp", { ascending: false }); // Fetch newest first within the range

      if (error) {
        console.error("Error fetching account history from Supabase:", error);
        // Return cache even if fetch fails, better than nothing
        return cachedSnapshots;
      }

      // Convert snake_case to camelCase
      newlyFetchedSnapshots = (data || []).map((item) => ({
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

      // 4. Save *only the newly fetched* data to IndexedDB
      if (newlyFetchedSnapshots.length > 0) {
        await saveSnapshotsToDB(newlyFetchedSnapshots);
      } else {
        console.log("[Data Service] No new snapshots fetched from Supabase.");
      }
    } else {
      console.log(
        "[Data Service] Cache is up to date. No Supabase fetch needed."
      );
    }

    // 5. Combine cached and newly fetched data
    // Use a Map to handle potential duplicates if fetch range overlaps slightly
    const combinedMap = new Map<string, AccountSnapshot>();
    cachedSnapshots.forEach((s) => combinedMap.set(s.timestamp, s));
    newlyFetchedSnapshots.forEach((s) => combinedMap.set(s.timestamp, s));

    const combinedSnapshots = Array.from(combinedMap.values());

    // 6. Sort the final combined array ascending for chart processing
    combinedSnapshots.sort(
      (a, b) =>
        new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
    );

    console.log("Final combined snapshots count:", combinedSnapshots.length);
    console.log("First timestamp returned:", combinedSnapshots?.[0]?.timestamp);
    console.log(
      "Last timestamp returned:",
      combinedSnapshots?.[combinedSnapshots?.length - 1]?.timestamp
    );

    return combinedSnapshots;
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
