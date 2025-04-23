import { openDB, DBSchema, IDBPDatabase } from "idb";
import { AccountSnapshot } from "./dataService"; // Assuming AccountSnapshot is exported

const DB_NAME = "TradingDashboardDB";
const STORE_NAME = "accountSnapshots";
const DB_VERSION = 1;

interface TradingDashboardDBSchema extends DBSchema {
  [STORE_NAME]: {
    key: string; // Using timestamp as key
    value: AccountSnapshot;
    indexes: { timestamp: string; environment: string }; // Add environment index
  };
}

let dbPromise: Promise<IDBPDatabase<TradingDashboardDBSchema>> | null = null;

function initDB(): Promise<IDBPDatabase<TradingDashboardDBSchema>> {
  if (!dbPromise) {
    dbPromise = openDB<TradingDashboardDBSchema>(DB_NAME, DB_VERSION, {
      upgrade(db) {
        if (!db.objectStoreNames.contains(STORE_NAME)) {
          const store = db.createObjectStore(STORE_NAME, {
            keyPath: "timestamp", // Use timestamp as the primary key
          });
          // Create indexes for efficient querying
          store.createIndex("timestamp", "timestamp");
          store.createIndex("environment", "environment");
        }
      },
    });
  }
  return dbPromise;
}

export async function saveSnapshotsToDB(
  snapshots: AccountSnapshot[]
): Promise<void> {
  if (!snapshots || snapshots.length === 0) {
    return;
  }
  try {
    const db = await initDB();
    const tx = db.transaction(STORE_NAME, "readwrite");
    const store = tx.objectStore(STORE_NAME);
    await Promise.all(snapshots.map((snapshot) => store.put(snapshot)));
    await tx.done;
    console.log(`[DB] Saved ${snapshots.length} snapshots to IndexedDB.`);
  } catch (error) {
    console.error("[DB] Error saving snapshots:", error);
  }
}

export async function getSnapshotsFromDB(
  startTimeISO: string,
  endTimeISO: string,
  environment: string
): Promise<AccountSnapshot[]> {
  try {
    const db = await initDB();
    const tx = db.transaction(STORE_NAME, "readonly");
    const store = tx.objectStore(STORE_NAME);
    const index = store.index("timestamp"); // Use the timestamp index

    // Create a key range for the query
    const range = IDBKeyRange.bound(startTimeISO, endTimeISO);

    const results = await index.getAll(range);
    await tx.done;

    // Filter results by environment client-side as compound index is not straightforward
    const filteredResults = results.filter(
      (snapshot) => snapshot.environment === environment
    );

    console.log(
      `[DB] Retrieved ${filteredResults.length} snapshots from IndexedDB for range ${startTimeISO} to ${endTimeISO} [${environment}].`
    );
    return filteredResults;
  } catch (error) {
    console.error("[DB] Error getting snapshots:", error);
    return [];
  }
}

// Optional: Function to clear old data if needed
export async function clearOldSnapshotsFromDB(
  cutoffDateISO: string
): Promise<void> {
  try {
    const db = await initDB();
    const tx = db.transaction(STORE_NAME, "readwrite");
    const store = tx.objectStore(STORE_NAME);
    const index = store.index("timestamp");
    const range = IDBKeyRange.upperBound(cutoffDateISO, true); // Delete keys <= cutoffDate
    let cursor = await index.openCursor(range);
    while (cursor) {
      await cursor.delete();
      cursor = await cursor.continue();
    }
    await tx.done;
    console.log(`[DB] Cleared snapshots older than ${cutoffDateISO}.`);
  } catch (error) {
    console.error("[DB] Error clearing old snapshots:", error);
  }
}
