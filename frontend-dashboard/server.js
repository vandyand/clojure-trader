const express = require("express");
const axios = require("axios");
const cors = require("cors");
const path = require("path");
const dotenv = require("dotenv");

// Load environment variables from .env and .env.server
dotenv.config();
dotenv.config({ path: ".env.server" });

const app = express();
app.use(cors());
app.use(express.json());

// Serve static files from the React app
app.use(express.static(path.join(__dirname, "build")));

// Proxy for Oanda API requests
app.all("/api/oanda/:endpoint(*)", async (req, res) => {
  try {
    // Get environment (LIVE or DEMO) from query param or default to env setting
    const dataSource =
      req.query.dataSource ||
      process.env.REACT_APP_OANDA_LIVE_OR_DEMO ||
      "DEMO";
    delete req.query.dataSource; // Remove from query params before forwarding

    // Get the appropriate base URL and API key based on the environment
    const baseURL =
      dataSource === "LIVE"
        ? process.env.REACT_APP_OANDA_LIVE_URL
        : process.env.REACT_APP_OANDA_DEMO_URL;

    const apiKey =
      dataSource === "LIVE"
        ? process.env.REACT_APP_OANDA_LIVE_KEY
        : process.env.REACT_APP_OANDA_DEMO_KEY;

    const accountId =
      dataSource === "LIVE"
        ? process.env.REACT_APP_OANDA_LIVE_ACCOUNT_ID
        : process.env.REACT_APP_OANDA_DEMO_ACCOUNT_ID;

    // Replace placeholder with actual account ID if present
    let endpoint = req.params.endpoint;
    if (endpoint.includes("{accountId}")) {
      endpoint = endpoint.replace("{accountId}", accountId);
    }

    const url = `${baseURL}${endpoint}`;

    // Forward the request to Oanda with the appropriate headers
    const response = await axios({
      method: req.method,
      url: url,
      headers: {
        Authorization: `Bearer ${apiKey}`,
        "Content-Type": "application/json",
      },
      params: req.query,
      data: req.method !== "GET" ? req.body : undefined,
    });

    res.json(response.data);
  } catch (error) {
    console.error("Error proxying to Oanda:", error.message);
    res.status(error.response?.status || 500).json({
      error: "Failed to fetch data from Oanda",
      message: error.message,
      details: error.response?.data,
    });
  }
});

// For React Router - handle all other requests by sending the React app
app.get("*", (req, res) => {
  res.sendFile(path.join(__dirname, "build", "index.html"));
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`Server running on port ${PORT}`));
