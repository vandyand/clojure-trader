const { createClient } = require("@supabase/supabase-js");
require("dotenv").config();
const axios = require("axios");

// For Node.js environments
const fetch = require("node-fetch");
global.fetch = fetch;

// Configure Supabase client
const supabaseUrl = process.env.REACT_APP_SUPABASE_URL;
const supabaseKey = process.env.REACT_APP_SUPABASE_ANON_KEY;

if (!supabaseUrl || !supabaseKey) {
  console.error(
    "Missing Supabase credentials. Set REACT_APP_SUPABASE_URL and REACT_APP_SUPABASE_ANON_KEY in your .env file."
  );
  process.exit(1);
}

const supabase = createClient(supabaseUrl, supabaseKey);

// Configure OANDA clients for both environments
const demoConfig = {
  baseURL:
    process.env.REACT_APP_OANDA_DEMO_URL ||
    "https://api-fxpractice.oanda.com/v3/",
  apiKey: process.env.REACT_APP_OANDA_DEMO_KEY || "",
  accountId: process.env.REACT_APP_OANDA_DEMO_ACCOUNT_ID || "",
};

const liveConfig = {
  baseURL:
    process.env.REACT_APP_OANDA_LIVE_URL || "https://api-fxtrade.oanda.com/v3/",
  apiKey: process.env.REACT_APP_OANDA_LIVE_KEY || "",
  accountId: process.env.REACT_APP_OANDA_LIVE_ACCOUNT_ID || "",
};

const demoClient = axios.create({
  baseURL: demoConfig.baseURL,
  headers: {
    Authorization: `Bearer ${demoConfig.apiKey}`,
    "Content-Type": "application/json",
    "Accept-Datetime-Format": "RFC3339",
  },
});

const liveClient = axios.create({
  baseURL: liveConfig.baseURL,
  headers: {
    Authorization: `Bearer ${liveConfig.apiKey}`,
    "Content-Type": "application/json",
    "Accept-Datetime-Format": "RFC3339",
  },
});

// Function to fetch account summary from OANDA
async function getAccountSummary(client, accountId) {
  try {
    const response = await client.get(`accounts/${accountId}/summary`);
    return response.data;
  } catch (error) {
    console.error("Error fetching account summary:", error);
    throw error;
  }
}

// Function to fetch open positions from OANDA
async function getOpenPositions(client, accountId) {
  try {
    const response = await client.get(`accounts/${accountId}/openPositions`);
    return response.data;
  } catch (error) {
    console.error("Error fetching open positions:", error);
    throw error;
  }
}

// Function to save account snapshot to Supabase for a specific environment
async function saveAccountSnapshot(client, config, environment) {
  try {
    console.log(
      `Fetching account data from OANDA ${environment} environment...`
    );

    // Fetch current account data
    const accountSummary = await getAccountSummary(client, config.accountId);
    const openPositions = await getOpenPositions(client, config.accountId);

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
      environment: environment,
    };

    console.log(`Saving ${environment} snapshot to Supabase:`, snapshot);

    // Save to Supabase
    const { error } = await supabase.from("account_snapshots").insert(snapshot);

    if (error) {
      console.error(`Error saving ${environment} account snapshot:`, error);
      return false;
    }

    console.log(`${environment} snapshot saved successfully!`);
    return true;
  } catch (error) {
    console.error(`Error in saveAccountSnapshot for ${environment}:`, error);
    return false;
  }
}

// Main function to run the process
async function runDataCollection() {
  console.log(
    `[${new Date().toISOString()}] Running scheduled data collection...`
  );

  try {
    // Process demo account
    const demoResult = await saveAccountSnapshot(
      demoClient,
      demoConfig,
      "DEMO"
    );

    // Process live account
    const liveResult = await saveAccountSnapshot(
      liveClient,
      liveConfig,
      "LIVE"
    );

    if (demoResult && liveResult) {
      console.log(
        `[${new Date().toISOString()}] Data collection completed successfully for both environments`
      );
    } else if (demoResult) {
      console.log(
        `[${new Date().toISOString()}] Data collection completed successfully for DEMO environment only`
      );
    } else if (liveResult) {
      console.log(
        `[${new Date().toISOString()}] Data collection completed successfully for LIVE environment only`
      );
    } else {
      console.log(
        `[${new Date().toISOString()}] Data collection failed for both environments`
      );
    }
  } catch (error) {
    console.error(
      `[${new Date().toISOString()}] Error in data collection:`,
      error
    );
  }
}

// Run immediately on start
runDataCollection();

// Then run every 15 minutes
const FIFTEEN_MINUTES = 15 * 60 * 1000;
setInterval(runDataCollection, FIFTEEN_MINUTES);

// Keep the process alive
process.on("SIGTERM", () => {
  console.log("SIGTERM received, shutting down gracefully");
  process.exit(0);
});
