const { createClient } = require("@supabase/supabase-js");
require("dotenv").config({ path: "./frontend-dashboard/.env" });

// Configure Supabase client
const supabaseUrl = process.env.REACT_APP_SUPABASE_URL;
const supabaseKey = process.env.REACT_APP_SUPABASE_ANON_KEY;

if (!supabaseUrl || !supabaseKey) {
  console.error(
    "Missing Supabase credentials. Make sure .env file exists with REACT_APP_SUPABASE_URL and REACT_APP_SUPABASE_ANON_KEY variables."
  );
  process.exit(1);
}

const supabase = createClient(supabaseUrl, supabaseKey);

async function checkLatestSnapshots() {
  try {
    console.log("Fetching the latest 5 snapshots for each environment...");

    // Get the latest 5 DEMO snapshots
    const { data: demoSnapshots, error: demoError } = await supabase
      .from("account_snapshots")
      .select("id, timestamp, environment, balance, unrealized_pl")
      .eq("environment", "DEMO")
      .order("timestamp", { ascending: false })
      .limit(5);

    if (demoError) {
      console.error("Error fetching DEMO snapshots:", demoError);
    } else {
      console.log("\nLatest DEMO snapshots:");
      demoSnapshots.forEach((snapshot) => {
        console.log(
          `${snapshot.timestamp} | Balance: ${snapshot.balance} | PL: ${snapshot.unrealized_pl}`
        );
      });
    }

    // Get the latest 5 LIVE snapshots
    const { data: liveSnapshots, error: liveError } = await supabase
      .from("account_snapshots")
      .select("id, timestamp, environment, balance, unrealized_pl")
      .eq("environment", "LIVE")
      .order("timestamp", { ascending: false })
      .limit(5);

    if (liveError) {
      console.error("Error fetching LIVE snapshots:", liveError);
    } else {
      console.log("\nLatest LIVE snapshots:");
      liveSnapshots.forEach((snapshot) => {
        console.log(
          `${snapshot.timestamp} | Balance: ${snapshot.balance} | PL: ${snapshot.unrealized_pl}`
        );
      });
    }
  } catch (error) {
    console.error("Error:", error);
  }
}

checkLatestSnapshots();
