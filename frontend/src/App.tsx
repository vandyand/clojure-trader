import React from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AccountSummary } from "./components/AccountSummary";
import { PositionsList } from "./components/PositionsList";
import { PerformanceChart } from "./components/PerformanceChart";
import { D3PositionsPerformanceChart } from "./components/D3PositionsPerformanceChart";
import { DataSourceProvider } from "./lib/DataSourceContext";
import { DataSourceToggle } from "./components/DataSourceToggle";
import "./App.css";

// Create a client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: true,
      staleTime: 5 * 60 * 1000, // Consider data stale after 5 minutes
      cacheTime: 10 * 60 * 1000, // Keep unused data in cache for 10 minutes
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <DataSourceProvider>
        <div className="App">
          <header className="App-header">
            <h1>Forex Trading Dashboard</h1>
            <div className="header-controls">
              <DataSourceToggle />
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

            <div className="grid-item positions-performance-chart-container">
              <D3PositionsPerformanceChart />
            </div>
          </main>

          <footer className="App-footer">
            <p>© {new Date().getFullYear()} Forex Trading Dashboard</p>
          </footer>
        </div>
      </DataSourceProvider>
    </QueryClientProvider>
  );
}

export default App;
