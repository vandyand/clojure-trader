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

// Configure OANDA client
const ENV =
  process.env.REACT_APP_OANDA_LIVE_OR_DEMO === "LIVE" ? "LIVE" : "DEMO";
const config = {
  baseURL:
    ENV === "LIVE"
      ? process.env.REACT_APP_OANDA_LIVE_URL ||
        "https://api-fxtrade.oanda.com/v3/"
      : process.env.REACT_APP_OANDA_DEMO_URL ||
        "https://api-fxpractice.oanda.com/v3/",
  apiKey:
    ENV === "LIVE"
      ? process.env.REACT_APP_OANDA_LIVE_KEY || ""
      : process.env.REACT_APP_OANDA_DEMO_KEY || "",
  accountId:
    ENV === "LIVE"
      ? process.env.REACT_APP_OANDA_LIVE_ACCOUNT_ID || ""
      : process.env.REACT_APP_OANDA_DEMO_ACCOUNT_ID || "",
};

const oandaClient = axios.create({
  baseURL: config.baseURL,
  headers: {
    Authorization: `Bearer ${config.apiKey}`,
    "Content-Type": "application/json",
    "Accept-Datetime-Format": "RFC3339",
  },
});

// Function to fetch account summary from OANDA
async function getAccountSummary() {
  try {
    const response = await oandaClient.get(
      `accounts/${config.accountId}/summary`
    );
    return response.data;
  } catch (error) {
    console.error("Error fetching account summary:", error);
    throw error;
  }
}

// Function to fetch open positions from OANDA
async function getOpenPositions() {
  try {
    const response = await oandaClient.get(
      `accounts/${config.accountId}/openPositions`
    );
    return response.data;
  } catch (error) {
    console.error("Error fetching open positions:", error);
    throw error;
  }
}

// Function to save account snapshot to Supabase
async function saveAccountSnapshot() {
  try {
    console.log("Fetching account data from OANDA...");

    // Fetch current account data
    const accountSummary = await getAccountSummary();
    const openPositions = await getOpenPositions();

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
      environment: ENV,
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

// Main function to run the process
async function runDataCollection() {
  console.log(
    `[${new Date().toISOString()}] Running scheduled data collection...`
  );

  try {
    await saveAccountSnapshot();
    console.log(
      `[${new Date().toISOString()}] Data collection completed successfully`
    );
  } catch (error) {
    console.error(
      `[${new Date().toISOString()}] Error in data collection:`,
      error
    );
  }
}

// Run immediately on start
runDataCollection();

// Then run every 5 minutes
const FIVE_MINUTES = 5 * 60 * 1000;
setInterval(runDataCollection, FIVE_MINUTES);

// Keep the process alive
process.on("SIGTERM", () => {
  console.log("SIGTERM received, shutting down gracefully");
  process.exit(0);
});
