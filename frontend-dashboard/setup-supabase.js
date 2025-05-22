const { createClient } = require("@supabase/supabase-js");
const fs = require("fs");
require("dotenv").config();
// For Node.js environments
const fetch = require("node-fetch");
global.fetch = fetch;

async function initializeSupabase() {
  console.log("Initializing Supabase...");

  // Get environment variables
  const supabaseUrl = process.env.REACT_APP_SUPABASE_URL;
  const supabaseKey = process.env.REACT_APP_SUPABASE_ANON_KEY;

  if (!supabaseUrl || !supabaseKey) {
    console.error(
      "Missing Supabase credentials. Set REACT_APP_SUPABASE_URL and REACT_APP_SUPABASE_ANON_KEY in your .env file."
    );
    process.exit(1);
  }

  // Create a Supabase client
  const supabase = createClient(supabaseUrl, supabaseKey);

  try {
    // Read SQL file
    const sql = fs.readFileSync("./supabase/schema.sql", "utf8");

    // Execute SQL
    console.log("Creating tables and setting up RLS...");

    // We'll execute each statement separately
    const statements = sql
      .split(";")
      .filter((statement) => statement.trim().length > 0);

    for (const statement of statements) {
      console.log(`Executing statement: ${statement.trim()}`);
      try {
        const { error } = await supabase.rpc("pgexec", {
          command: statement.trim() + ";",
        });

        if (error) {
          console.error("Error executing SQL statement:", error);
          console.log("Statement:", statement);
        } else {
          console.log("Statement executed successfully");
        }
      } catch (err) {
        console.error("Error executing statement:", err);
        console.log("Statement:", statement);
      }
    }

    console.log("Database setup complete!");
  } catch (error) {
    console.error("Error setting up database:", error);
    process.exit(1);
  }
}

initializeSupabase().catch((error) => {
  console.error("Unhandled error:", error);
  process.exit(1);
});
