import React, { useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { useTradingContext } from "../context/TradingContext";
import { formatDate, formatCurrency } from "../utils/formatters";

interface TimeRangeOption {
  label: string;
  value: number; // days
}

const timeRangeOptions: TimeRangeOption[] = [
  { label: "1W", value: 7 },
  { label: "1M", value: 30 },
  { label: "3M", value: 90 },
  { label: "All", value: 0 },
];

const PerformanceChart: React.FC = () => {
  const { performance, isLoading } = useTradingContext();
  const [timeRange, setTimeRange] = useState<number>(30); // Default to 30 days

  // Filter data based on selected time range
  const filteredData =
    timeRange === 0
      ? performance
      : performance.filter((p) => {
          const date = new Date(p.timestamp);
          const now = new Date();
          const diffTime = Math.abs(now.getTime() - date.getTime());
          const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
          return diffDays <= timeRange;
        });

  // Format data for the chart
  const chartData = filteredData.map((p) => ({
    date: p.timestamp,
    value: p.value,
    formattedDate: formatDate(p.timestamp, "MMM dd"),
  }));

  if (isLoading && !performance.length) {
    return (
      <div className="card animate-pulse">
        <div className="h-8 bg-gray-200 rounded w-1/3 mb-4"></div>
        <div className="h-64 bg-gray-200 rounded w-full"></div>
      </div>
    );
  }

  // Calculate performance metrics
  const initialValue = chartData[0]?.value || 0;
  const currentValue = chartData[chartData.length - 1]?.value || 0;
  const absoluteChange = currentValue - initialValue;
  const percentageChange = (absoluteChange / initialValue) * 100;

  return (
    <div className="card">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-lg font-semibold text-gray-800">
          Portfolio Performance
        </h2>
        <div className="flex space-x-2">
          {timeRangeOptions.map((option) => (
            <button
              key={option.value}
              className={`px-3 py-1 text-sm rounded-md ${
                timeRange === option.value
                  ? "bg-blue-600 text-white"
                  : "bg-gray-100 text-gray-700 hover:bg-gray-200"
              }`}
              onClick={() => setTimeRange(option.value)}
            >
              {option.label}
            </button>
          ))}
        </div>
      </div>

      <div className="flex justify-between items-start mb-4">
        <div>
          <span className="block text-sm text-gray-500">Current Value</span>
          <span className="text-2xl font-bold">
            {formatCurrency(currentValue)}
          </span>
        </div>
        <div className="text-right">
          <span className="block text-sm text-gray-500">Change</span>
          <div className={absoluteChange >= 0 ? "gain" : "loss"}>
            <span className="text-lg font-bold">
              {absoluteChange >= 0 ? "+" : ""}
              {formatCurrency(absoluteChange)}
            </span>
            <span className="ml-1">
              ({absoluteChange >= 0 ? "+" : ""}
              {percentageChange.toFixed(2)}%)
            </span>
          </div>
        </div>
      </div>

      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart
            data={chartData}
            margin={{ top: 5, right: 5, left: 5, bottom: 5 }}
          >
            <CartesianGrid strokeDasharray="3 3" vertical={false} />
            <XAxis
              dataKey="formattedDate"
              tickMargin={10}
              tick={{ fontSize: 12 }}
              tickFormatter={(value) => formatDate(value, "MMM dd")}
            />
            <YAxis
              tickFormatter={(value) => formatCurrency(value, "USD", "en-US")}
              tick={{ fontSize: 12 }}
              width={80}
              domain={["dataMin - 100", "dataMax + 100"]}
            />
            <Tooltip
              formatter={(value: number) => [formatCurrency(value), "Value"]}
              labelFormatter={(label) => formatDate(label, "MMM dd, yyyy")}
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
        </ResponsiveContainer>
      </div>
    </div>
  );
};

export default PerformanceChart;
