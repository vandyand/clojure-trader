import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { format } from "date-fns";
import * as dataService from "../lib/dataService";

interface PerformanceChartProps {
  refreshInterval?: number;
}

interface PerformanceData {
  date: string;
  nav: number;
  dailyChange: number;
  dailyChangePercent: number;
}

export const PerformanceChart: React.FC<PerformanceChartProps> = ({
  refreshInterval = 60000 * 5, // 5 minutes default refresh
}) => {
  const [timeRange, setTimeRange] = useState(30); // Default 30 days

  const { data, isLoading, error } = useQuery({
    queryKey: ["performance", timeRange],
    queryFn: () => dataService.getDailyPerformance(timeRange),
    refetchInterval: refreshInterval,
  });

  if (isLoading) return <div>Loading performance data...</div>;
  if (error) return <div>Error loading performance data</div>;
  if (!data || data.length === 0) {
    return (
      <div className="performance-chart empty">
        <h2>Account Performance</h2>
        <p>
          No performance data available. Data will be collected as you use the
          dashboard.
        </p>
        <div className="time-range-selector">
          <button
            onClick={() => setTimeRange(7)}
            className={timeRange === 7 ? "active" : ""}
          >
            7 Days
          </button>
          <button
            onClick={() => setTimeRange(30)}
            className={timeRange === 30 ? "active" : ""}
          >
            30 Days
          </button>
          <button
            onClick={() => setTimeRange(90)}
            className={timeRange === 90 ? "active" : ""}
          >
            90 Days
          </button>
        </div>
      </div>
    );
  }

  // Calculate overall performance
  const firstValue = data[0].nav;
  const lastValue = data[data.length - 1].nav;
  const totalChange = lastValue - firstValue;
  const totalChangePercent = (totalChange / firstValue) * 100;

  // Format dates for chart
  const formattedData = data.map((item) => ({
    ...item,
    formattedDate: format(new Date(item.date), "MMM dd"),
  }));

  return (
    <div className="performance-chart">
      <h2>Account Performance</h2>

      <div className="overall-performance">
        <div className="metric">
          <span className="label">Total Change:</span>
          <span className={totalChange >= 0 ? "positive" : "negative"}>
            ${totalChange.toFixed(2)}
          </span>
        </div>
        <div className="metric">
          <span className="label">Total Change (%):</span>
          <span className={totalChangePercent >= 0 ? "positive" : "negative"}>
            {totalChangePercent.toFixed(2)}%
          </span>
        </div>
      </div>

      <div className="time-range-selector">
        <button
          onClick={() => setTimeRange(7)}
          className={timeRange === 7 ? "active" : ""}
        >
          7 Days
        </button>
        <button
          onClick={() => setTimeRange(30)}
          className={timeRange === 30 ? "active" : ""}
        >
          30 Days
        </button>
        <button
          onClick={() => setTimeRange(90)}
          className={timeRange === 90 ? "active" : ""}
        >
          90 Days
        </button>
      </div>

      <div className="chart-container" style={{ width: "100%", height: 300 }}>
        <ResponsiveContainer>
          <LineChart
            data={formattedData}
            margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
          >
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="formattedDate" />
            <YAxis
              domain={["auto", "auto"]}
              tickFormatter={(value) => `$${value}`}
            />
            <Tooltip
              formatter={(value) => [`$${Number(value).toFixed(2)}`, "NAV"]}
              labelFormatter={(value) => `Date: ${value}`}
            />
            <Line
              type="monotone"
              dataKey="nav"
              stroke="#2451B7"
              activeDot={{ r: 8 }}
              name="NAV"
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};
