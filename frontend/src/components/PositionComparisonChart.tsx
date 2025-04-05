import React, { useState, useEffect } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { Position } from "../api/tradingService";
import { getPositionPerformance } from "../utils/timeSeriesStorage";
import { format, subDays, subWeeks, subMonths } from "date-fns";
import { formatDate, formatCurrency } from "../utils/formatters";

// Date range options
type DateRange = "1w" | "1m" | "3m" | "all";

interface PositionComparisonChartProps {
  positions: Position[];
}

const PositionComparisonChart: React.FC<PositionComparisonChartProps> = ({
  positions,
}) => {
  const [dateRange, setDateRange] = useState<DateRange>("1m");
  const [chartData, setChartData] = useState<Array<any>>([]);

  // Line colors for each position
  const colors = [
    "#3b82f6", // blue
    "#22c55e", // green
    "#ef4444", // red
    "#f59e0b", // amber
    "#8b5cf6", // purple
    "#06b6d4", // cyan
    "#ec4899", // pink
    "#10b981", // emerald
    "#6366f1", // indigo
    "#f97316", // orange
  ];

  useEffect(() => {
    if (!positions.length) return;

    // Calculate start date based on selected range
    let startTimestamp: number;
    const now = new Date();

    switch (dateRange) {
      case "1w":
        startTimestamp = subDays(now, 7).getTime();
        break;
      case "1m":
        startTimestamp = subMonths(now, 1).getTime();
        break;
      case "3m":
        startTimestamp = subMonths(now, 3).getTime();
        break;
      case "all":
      default:
        startTimestamp = 0;
        break;
    }

    // Get instrument names
    const instruments = positions.map((pos) => pos.instrument);

    // Get performance data for each position
    const positionData = getPositionPerformance(instruments, startTimestamp);

    // Merge data for chart (by timestamp)
    const timestampMap: Record<number, Record<string, number>> = {};

    // Populate the map with all timestamps and values
    Object.entries(positionData).forEach(([instrument, dataPoints]) => {
      dataPoints.forEach(({ timestamp, normalizedValue }) => {
        if (!timestampMap[timestamp]) {
          timestampMap[timestamp] = { timestamp };
        }
        timestampMap[timestamp][instrument] = normalizedValue;
      });
    });

    // Convert map to array and sort by timestamp
    const mergedData = Object.values(timestampMap).sort(
      (a: any, b: any) => a.timestamp - b.timestamp
    );

    // Format timestamps for display
    mergedData.forEach((point: any) => {
      point.formattedDate = format(new Date(point.timestamp), "MMM dd, yyyy");
    });

    setChartData(mergedData);
  }, [positions, dateRange]);

  // Handle if we have no data
  if (chartData.length === 0) {
    return (
      <div className="p-6 bg-white rounded-lg shadow-md">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-lg font-semibold">
            Position Performance Comparison
          </h2>
          <div className="flex space-x-2">
            <RangeButton
              range="1w"
              current={dateRange}
              onClick={setDateRange}
            />
            <RangeButton
              range="1m"
              current={dateRange}
              onClick={setDateRange}
            />
            <RangeButton
              range="3m"
              current={dateRange}
              onClick={setDateRange}
            />
            <RangeButton
              range="all"
              current={dateRange}
              onClick={setDateRange}
            />
          </div>
        </div>
        <div className="h-64 flex items-center justify-center bg-gray-50 rounded-md">
          <p className="text-gray-500">
            Not enough historical data available for comparison. Data will begin
            to populate as trading activity occurs.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 bg-white rounded-lg shadow-md">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-lg font-semibold">
          Position Performance Comparison
        </h2>
        <div className="flex space-x-2">
          <RangeButton range="1w" current={dateRange} onClick={setDateRange} />
          <RangeButton range="1m" current={dateRange} onClick={setDateRange} />
          <RangeButton range="3m" current={dateRange} onClick={setDateRange} />
          <RangeButton range="all" current={dateRange} onClick={setDateRange} />
        </div>
      </div>

      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart
            data={chartData}
            margin={{ top: 5, right: 30, left: 0, bottom: 5 }}
          >
            <CartesianGrid strokeDasharray="3 3" vertical={false} />
            <XAxis
              dataKey="formattedDate"
              tick={{ fontSize: 12 }}
              tickMargin={10}
              tickFormatter={(value) => {
                // Don't reformat if already formatted
                if (typeof value === "string" && value.includes(",")) {
                  return value;
                }
                return formatDate(value, "MMM dd");
              }}
            />
            <YAxis
              domain={["dataMin - 0.05", "dataMax + 0.05"]}
              tickFormatter={(value) => value.toFixed(2)}
              tick={{ fontSize: 12 }}
            />
            <Tooltip
              formatter={(value: number, name: string) => [
                formatCurrency(value),
                name === "costBasis" ? "Cost Basis" : "Current Value",
              ]}
              labelFormatter={(label) => {
                // Handle different label formats depending on what we receive
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

                // If all else fails, return the original label
                console.log("Debug - unable to format date label:", label);
                return String(label);
              }}
            />
            <Legend verticalAlign="top" height={36} />

            {positions.map((position, index) => (
              <Line
                key={position.instrument}
                type="monotone"
                dataKey={position.instrument}
                name={position.instrument}
                stroke={colors[index % colors.length]}
                dot={false}
                activeDot={{ r: 6 }}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="mt-4 text-center text-xs text-gray-500">
        * Each position is normalized to 1.0 at the start of the selected time
        period
      </div>
    </div>
  );
};

// Date range button component
interface RangeButtonProps {
  range: DateRange;
  current: DateRange;
  onClick: (range: DateRange) => void;
}

const RangeButton: React.FC<RangeButtonProps> = ({
  range,
  current,
  onClick,
}) => {
  const isActive = range === current;
  const baseClasses =
    "px-3 py-1 text-sm font-medium rounded-md transition-colors";
  const activeClasses = "bg-blue-600 text-white";
  const inactiveClasses = "bg-gray-200 text-gray-800 hover:bg-gray-300";

  return (
    <button
      onClick={() => onClick(range)}
      className={`${baseClasses} ${isActive ? activeClasses : inactiveClasses}`}
    >
      {range === "1w"
        ? "1W"
        : range === "1m"
        ? "1M"
        : range === "3m"
        ? "3M"
        : "All"}
    </button>
  );
};

export default PositionComparisonChart;
