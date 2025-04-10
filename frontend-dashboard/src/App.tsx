import React from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AccountSummary } from "./components/AccountSummary";
import { PositionsList } from "./components/PositionsList";
import { PerformanceChart } from "./components/PerformanceChart";
import "./App.css";

// Create a client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <div className="App">
        <header className="App-header">
          <h1>Forex Trading Dashboard</h1>
          <div className="environment-label">
            {process.env.REACT_APP_OANDA_LIVE_OR_DEMO === "LIVE"
              ? "LIVE"
              : "DEMO"}{" "}
            Environment
          </div>
        </header>

        <main className="dashboard-grid">
          <div className="grid-item account-summary-container">
            <AccountSummary />
          </div>

          <div className="grid-item performance-chart-container">
            <PerformanceChart />
          </div>

          <div className="grid-item positions-list-container">
            <PositionsList />
          </div>
        </main>

        <footer className="App-footer">
          <p>© {new Date().getFullYear()} Forex Trading Dashboard</p>
        </footer>
      </div>
    </QueryClientProvider>
  );
}

export default App;
