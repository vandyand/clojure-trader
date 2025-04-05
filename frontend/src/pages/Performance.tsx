import React, { useState } from "react";
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import { useTradingContext } from "../context/TradingContext";
import { formatDate, formatCurrency } from "../utils/formatters";

type ChartType = "area" | "line" | "bar";
type TimeFrame = "1W" | "1M" | "3M" | "6M" | "1Y" | "All";

const timeFrameOptions: { label: TimeFrame; days: number }[] = [
  { label: "1W", days: 7 },
  { label: "1M", days: 30 },
  { label: "3M", days: 90 },
  { label: "6M", days: 180 },
  { label: "1Y", days: 365 },
  { label: "All", days: 0 },
];

const Performance: React.FC = () => {
  const { performance, isLoading } = useTradingContext();
  const [chartType, setChartType] = useState<ChartType>("area");
  const [timeFrame, setTimeFrame] = useState<TimeFrame>("1M");

  // Filter data based on selected time frame
  const filteredData = (() => {
    const selectedTimeFrame = timeFrameOptions.find(
      (t) => t.label === timeFrame
    );
    if (!selectedTimeFrame || selectedTimeFrame.days === 0) return performance;

    const cutoffDate = new Date();
    cutoffDate.setDate(cutoffDate.getDate() - selectedTimeFrame.days);
    const cutoffTimestamp = cutoffDate.getTime();

    return performance.filter((p) => p.timestamp >= cutoffTimestamp);
  })();

  const chartData = filteredData.map((p) => {
    // Create a proper Date object
    const dateObj = new Date(p.timestamp);

    return {
      date: p.timestamp,
      dateObj, // Add date object for direct access
      value: p.value,
      change: p.change,
      changePercent: p.changePercent,
      formattedDate: formatDate(dateObj, "MMM dd, yyyy"),
    };
  });

  // Calculate performance metrics
  const calculateMetrics = (data: typeof chartData) => {
    if (!data.length)
      return {
        totalReturn: 0,
        averageReturn: 0,
        volatility: 0,
        sharpeRatio: 0,
        maxDrawdown: 0,
      };

    const initialValue = data[0]?.value || 0;
    const currentValue = data[data.length - 1]?.value || 0;
    const totalReturn = ((currentValue - initialValue) / initialValue) * 100;

    // Daily returns
    const dailyReturns = data.map((d) => d.changePercent);
    const averageReturn =
      dailyReturns.reduce((sum, val) => sum + val, 0) / dailyReturns.length;

    // Volatility (standard deviation of returns)
    const squaredDiffs = dailyReturns.map((r) =>
      Math.pow(r - averageReturn, 2)
    );
    const avgSquaredDiff =
      squaredDiffs.reduce((sum, val) => sum + val, 0) / squaredDiffs.length;
    const volatility = Math.sqrt(avgSquaredDiff);

    // Sharpe Ratio (using 0% as risk-free rate for simplicity)
    const sharpeRatio = volatility === 0 ? 0 : averageReturn / volatility;

    // Maximum Drawdown
    let maxDrawdown = 0;
    let peak = data[0]?.value || 0;

    for (const point of data) {
      if (point.value > peak) {
        peak = point.value;
      } else {
        const drawdown = ((peak - point.value) / peak) * 100;
        if (drawdown > maxDrawdown) {
          maxDrawdown = drawdown;
        }
      }
    }

    return {
      totalReturn,
      averageReturn,
      volatility,
      sharpeRatio,
      maxDrawdown,
    };
  };

  const metrics = calculateMetrics(chartData);

  if (isLoading && !performance.length) {
    return (
      <div>
        <h1 className="text-2xl font-bold text-gray-800 mb-6">
          Performance Analytics
        </h1>
        <div className="card animate-pulse">
          <div className="h-8 bg-gray-200 rounded w-1/3 mb-4"></div>
          <div className="h-64 bg-gray-200 rounded w-full"></div>
        </div>
      </div>
    );
  }

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-800 mb-6">
        Performance Analytics
      </h1>

      <div className="card mb-6">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between mb-6">
          <h2 className="text-lg font-semibold text-gray-800 mb-4 md:mb-0">
            Performance Chart
          </h2>

          <div className="flex flex-wrap gap-4">
            <div className="flex space-x-2">
              {timeFrameOptions.map((option) => (
                <button
                  key={option.label}
                  className={`px-3 py-1 text-sm rounded-md ${
                    timeFrame === option.label
                      ? "bg-blue-600 text-white"
                      : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                  }`}
                  onClick={() => setTimeFrame(option.label)}
                >
                  {option.label}
                </button>
              ))}
            </div>

            <div className="flex space-x-2">
              <button
                className={`px-3 py-1 text-sm rounded-md ${
                  chartType === "area"
                    ? "bg-blue-600 text-white"
                    : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                }`}
                onClick={() => setChartType("area")}
              >
                Area
              </button>
              <button
                className={`px-3 py-1 text-sm rounded-md ${
                  chartType === "line"
                    ? "bg-blue-600 text-white"
                    : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                }`}
                onClick={() => setChartType("line")}
              >
                Line
              </button>
              <button
                className={`px-3 py-1 text-sm rounded-md ${
                  chartType === "bar"
                    ? "bg-blue-600 text-white"
                    : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                }`}
                onClick={() => setChartType("bar")}
              >
                Bar
              </button>
            </div>
          </div>
        </div>

        <div className="h-80">
          <ResponsiveContainer width="100%" height="100%">
            {chartType === "area" ? (
              <AreaChart
                data={chartData}
                margin={{ top: 10, right: 30, left: 0, bottom: 0 }}
              >
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis
                  dataKey="formattedDate"
                  tickMargin={10}
                  tick={{ fontSize: 12 }}
                  tickFormatter={(value) => {
                    // Don't reformat if already formatted
                    if (typeof value === "string" && value.includes(",")) {
                      return value;
                    }
                    // Try to format with year
                    return formatDate(value, "MMM dd");
                  }}
                />
                <YAxis
                  tickFormatter={(value) =>
                    formatCurrency(value, "USD", "en-US")
                  }
                  tick={{ fontSize: 12 }}
                  width={80}
                />
                <Tooltip
                  formatter={(value: number) => [
                    formatCurrency(value),
                    "Value",
                  ]}
                  labelFormatter={(label) => {
                    // Handle different label formats depending on the chart component
                    if (typeof label === "object" && label.dateObj) {
                      return formatDate(label.dateObj, "MMM dd, yyyy");
                    }
                    if (typeof label === "string" && label.includes(",")) {
                      return label; // Already formatted correctly
                    }
                    // Try to parse as a date
                    const date = new Date(label);
                    if (!isNaN(date.getTime())) {
                      return formatDate(date, "MMM dd, yyyy");
                    }
                    return label;
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="value"
                  stroke="#3b82f6"
                  fill="#93c5fd"
                  activeDot={{ r: 6 }}
                />
              </AreaChart>
            ) : chartType === "line" ? (
              <LineChart
                data={chartData}
                margin={{ top: 10, right: 30, left: 0, bottom: 0 }}
              >
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis
                  dataKey="formattedDate"
                  tickMargin={10}
                  tick={{ fontSize: 12 }}
                  tickFormatter={(value) => {
                    // Don't reformat if already formatted
                    if (typeof value === "string" && value.includes(",")) {
                      return value;
                    }
                    // Try to format with year
                    return formatDate(value, "MMM dd");
                  }}
                />
                <YAxis
                  tickFormatter={(value) =>
                    formatCurrency(value, "USD", "en-US")
                  }
                  tick={{ fontSize: 12 }}
                  width={80}
                />
                <Tooltip
                  formatter={(value: number) => [
                    formatCurrency(value),
                    "Value",
                  ]}
                  labelFormatter={(label) => {
                    // Handle different label formats depending on the chart component
                    if (typeof label === "object" && label.dateObj) {
                      return formatDate(label.dateObj, "MMM dd, yyyy");
                    }
                    if (typeof label === "string" && label.includes(",")) {
                      return label; // Already formatted correctly
                    }
                    // Try to parse as a date
                    const date = new Date(label);
                    if (!isNaN(date.getTime())) {
                      return formatDate(date, "MMM dd, yyyy");
                    }
                    return label;
                  }}
                />
                <Line
                  type="monotone"
                  dataKey="value"
                  stroke="#3b82f6"
                  strokeWidth={2}
                  dot={false}
                  activeDot={{ r: 6 }}
                />
              </LineChart>
            ) : (
              <BarChart
                data={chartData}
                margin={{ top: 10, right: 30, left: 0, bottom: 0 }}
              >
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis
                  dataKey="formattedDate"
                  tickMargin={10}
                  tick={{ fontSize: 12 }}
                  tickFormatter={(value) => {
                    // Don't reformat if already formatted
                    if (typeof value === "string" && value.includes(",")) {
                      return value;
                    }
                    // Try to format with year
                    return formatDate(value, "MMM dd");
                  }}
                />
                <YAxis
                  tickFormatter={(value) =>
                    formatCurrency(value, "USD", "en-US")
                  }
                  tick={{ fontSize: 12 }}
                  width={80}
                />
                <Tooltip
                  formatter={(value: number) => [
                    formatCurrency(value),
                    "Value",
                  ]}
                  labelFormatter={(label) => {
                    // Handle different label formats depending on the chart component
                    if (typeof label === "object" && label.dateObj) {
                      return formatDate(label.dateObj, "MMM dd, yyyy");
                    }
                    if (typeof label === "string" && label.includes(",")) {
                      return label; // Already formatted correctly
                    }
                    // Try to parse as a date
                    const date = new Date(label);
                    if (!isNaN(date.getTime())) {
                      return formatDate(date, "MMM dd, yyyy");
                    }
                    return label;
                  }}
                />
                <Bar dataKey="value" fill="#3b82f6" />
              </BarChart>
            )}
          </ResponsiveContainer>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
        <div className="card">
          <h2 className="text-lg font-semibold text-gray-800 mb-4">
            Performance Metrics
          </h2>
          <div className="grid grid-cols-2 gap-4">
            <div className="p-4 bg-blue-50 rounded-md">
              <div className="text-sm text-gray-500">Total Return</div>
              <div
                className={`text-xl font-medium ${
                  metrics.totalReturn >= 0 ? "text-green-600" : "text-red-600"
                }`}
              >
                {metrics.totalReturn >= 0 ? "+" : ""}
                {metrics.totalReturn.toFixed(2)}%
              </div>
            </div>
            <div className="p-4 bg-blue-50 rounded-md">
              <div className="text-sm text-gray-500">Avg. Daily Return</div>
              <div
                className={`text-xl font-medium ${
                  metrics.averageReturn >= 0 ? "text-green-600" : "text-red-600"
                }`}
              >
                {metrics.averageReturn >= 0 ? "+" : ""}
                {metrics.averageReturn.toFixed(2)}%
              </div>
            </div>
            <div className="p-4 bg-blue-50 rounded-md">
              <div className="text-sm text-gray-500">Volatility</div>
              <div className="text-xl font-medium">
                {metrics.volatility.toFixed(2)}%
              </div>
            </div>
            <div className="p-4 bg-blue-50 rounded-md">
              <div className="text-sm text-gray-500">Sharpe Ratio</div>
              <div className="text-xl font-medium">
                {metrics.sharpeRatio.toFixed(2)}
              </div>
            </div>
            <div className="p-4 bg-blue-50 rounded-md col-span-2">
              <div className="text-sm text-gray-500">Maximum Drawdown</div>
              <div className="text-xl font-medium text-red-600">
                -{metrics.maxDrawdown.toFixed(2)}%
              </div>
            </div>
          </div>
        </div>

        <div className="card">
          <h2 className="text-lg font-semibold text-gray-800 mb-4">
            Daily Returns Distribution
          </h2>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={chartData.map((d) => ({
                  ...d,
                  dailyReturn: d.changePercent,
                }))}
                margin={{ top: 10, right: 10, left: 0, bottom: 0 }}
              >
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis
                  dataKey="formattedDate"
                  tickMargin={10}
                  tick={{ fontSize: 12 }}
                  tickFormatter={(value) => {
                    // Don't reformat if already formatted
                    if (typeof value === "string" && value.includes(",")) {
                      return value;
                    }
                    // Try to format with year
                    return formatDate(value, "MMM dd");
                  }}
                />
                <YAxis
                  tickFormatter={(value) => `${value.toFixed(2)}%`}
                  tick={{ fontSize: 12 }}
                />
                <Tooltip
                  formatter={(value: number) => [
                    `${value.toFixed(2)}%`,
                    "Daily Return",
                  ]}
                  labelFormatter={(label) => {
                    // Handle different label formats depending on the chart component
                    if (typeof label === "object" && label.dateObj) {
                      return formatDate(label.dateObj, "MMM dd, yyyy");
                    }
                    if (typeof label === "string" && label.includes(",")) {
                      return label; // Already formatted correctly
                    }
                    // Try to parse as a date
                    const date = new Date(label);
                    if (!isNaN(date.getTime())) {
                      return formatDate(date, "MMM dd, yyyy");
                    }
                    // If label is a number (timestamp), try converting
                    if (!isNaN(Number(label))) {
                      const dateFromTimestamp = new Date(Number(label));
                      if (!isNaN(dateFromTimestamp.getTime())) {
                        return formatDate(dateFromTimestamp, "MMM dd, yyyy");
                      }
                    }
                    return String(label);
                  }}
                />
                <Bar dataKey="dailyReturn" fill="#3b82f6">
                  {chartData.map((entry, index) => (
                    <Cell
                      key={`cell-${index}`}
                      fill={entry.changePercent >= 0 ? "#22c55e" : "#ef4444"}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      <div className="card">
        <h2 className="text-lg font-semibold text-gray-800 mb-4">
          Performance Analysis
        </h2>
        <p className="text-gray-600 mb-4">
          This dashboard displays the performance of your trading strategies
          over time. The metrics shown are calculated based on the historical
          data available and can help you assess the effectiveness of your
          strategies.
        </p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="p-4 border border-gray-200 rounded-md">
            <h3 className="font-medium text-gray-800 mb-2">
              Understanding the Metrics
            </h3>
            <ul className="text-sm text-gray-600 space-y-2 list-disc pl-5">
              <li>
                <strong>Total Return:</strong> The overall percentage gain/loss
                for the selected period.
              </li>
              <li>
                <strong>Avg. Daily Return:</strong> The mean percentage change
                per day.
              </li>
              <li>
                <strong>Volatility:</strong> Standard deviation of returns,
                indicating risk level.
              </li>
              <li>
                <strong>Sharpe Ratio:</strong> Risk-adjusted return metric
                (higher is better).
              </li>
              <li>
                <strong>Maximum Drawdown:</strong> Largest peak-to-trough
                decline in portfolio value.
              </li>
            </ul>
          </div>
          <div className="p-4 border border-gray-200 rounded-md">
            <h3 className="font-medium text-gray-800 mb-2">
              Strategy Insights
            </h3>
            <p className="text-sm text-gray-600">
              The performance data reflects the effectiveness of the genetic
              algorithm-based trading strategies employed by the Clojure
              backend. Strategy parameters are continuously optimized based on
              backtests and live performance data. The gains shown are a result
              of these optimizations.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Performance;
