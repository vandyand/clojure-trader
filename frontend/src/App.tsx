import React from "react";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { TradingProvider } from "./context/TradingContext";
import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import Positions from "./pages/Positions";
import Performance from "./pages/Performance";
import Backtests from "./pages/Backtests";
import "./App.css";

// Create a client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      staleTime: 60000, // 1 minute
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <TradingProvider>
        <Router>
          <Layout>
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/positions" element={<Positions />} />
              <Route path="/performance" element={<Performance />} />
              <Route path="/backtests" element={<Backtests />} />
            </Routes>
          </Layout>
        </Router>
      </TradingProvider>
    </QueryClientProvider>
  );
}

export default App;
