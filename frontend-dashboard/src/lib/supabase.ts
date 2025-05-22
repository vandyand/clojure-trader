import { createClient } from "@supabase/supabase-js";

// Using hardcoded values to ensure correct connection
const supabaseUrl = "https://juazmcbwhwwgepbwzhuw.supabase.co";
const supabaseKey = process.env.REACT_APP_SUPABASE_ANON_KEY || "";

// Add console logs for debugging
console.log("Supabase URL Loaded:", supabaseUrl);
console.log(
  "Supabase Key Loaded:",
  supabaseKey ? "*** Key Loaded ***" : "!!! Key Not Loaded !!!"
);

if (!supabaseUrl || !supabaseKey) {
  console.error("Missing Supabase credentials");
}

export const supabase = createClient(supabaseUrl, supabaseKey);
