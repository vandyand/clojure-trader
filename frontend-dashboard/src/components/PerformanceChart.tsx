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
import { format, subDays } from "date-fns";
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

type TimeRangeType = "preset" | "custom";
type GranularityType = "daily" | "hourly";

export const PerformanceChart: React.FC<PerformanceChartProps> = ({
  refreshInterval = 60000 * 5, // 5 minutes default refresh
}) => {
  // State for time range type (preset days or custom date range)
  const [timeRangeType, setTimeRangeType] = useState<TimeRangeType>("preset");

  // Preset days selection
  const [presetDays, setPresetDays] = useState(30); // Default 30 days

  // Custom date range
  const [startDate, setStartDate] = useState(() => {
    const date = new Date();
    date.setDate(date.getDate() - 30);
    return date.toISOString().split("T")[0];
  });
  const [endDate, setEndDate] = useState(() => {
    return new Date().toISOString().split("T")[0];
  });

  // Custom days input
  const [customDays, setCustomDays] = useState("");

  // Granularity selection
  const [granularity, setGranularity] = useState<GranularityType>("daily");

  // Calculate days based on selected time range type
  const getDaysForQuery = () => {
    if (timeRangeType === "preset") {
      return presetDays;
    } else {
      // Calculate days between start and end date
      const start = new Date(startDate);
      const end = new Date(endDate);
      const diffTime = Math.abs(end.getTime() - start.getTime());
      const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
      return diffDays + 1; // Include both start and end dates
    }
  };

  // Handle custom days input
  const handleCustomDaysSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const days = parseInt(customDays);
    if (!isNaN(days) && days > 0 && days <= 365) {
      setPresetDays(days);
      setTimeRangeType("preset");
    }
  };

  // Handle custom date range
  const handleDateRangeChange = () => {
    setTimeRangeType("custom");
  };

  const { data, isLoading, error } = useQuery({
    queryKey: [
      "performance",
      getDaysForQuery(),
      granularity,
      startDate,
      endDate,
      timeRangeType,
    ],
    queryFn: () => {
      // If custom date range, pass start and end dates to the API
      if (timeRangeType === "custom") {
        return dataService.getPerformanceByDateRange(
          startDate,
          endDate,
          granularity
        );
      }
      // Otherwise use preset days
      return dataService.getDailyPerformance(getDaysForQuery(), granularity);
    },
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
        {renderTimeControls()}
      </div>
    );
  }

  // Calculate overall performance
  const firstValue = data[0].nav;
  const lastValue = data[data.length - 1].nav;
  const totalChange = lastValue - firstValue;
  const totalChangePercent = (totalChange / firstValue) * 100;

  // Format dates for chart
  const formatDateByGranularity = (dateStr: string) => {
    const date = new Date(dateStr);
    return granularity === "hourly"
      ? format(date, "MMM dd HH:mm")
      : format(date, "MMM dd");
  };

  const formattedData = data.map((item) => ({
    ...item,
    formattedDate: formatDateByGranularity(item.date),
  }));

  // Function to render time controls
  function renderTimeControls() {
    return (
      <div className="time-controls">
        <div className="control-section">
          <div className="section-header">Time Range Type</div>
          <div className="toggle-buttons">
            <button
              onClick={() => setTimeRangeType("preset")}
              className={timeRangeType === "preset" ? "active" : ""}
            >
              Preset Days
            </button>
            <button
              onClick={() => setTimeRangeType("custom")}
              className={timeRangeType === "custom" ? "active" : ""}
            >
              Custom Date Range
            </button>
          </div>
        </div>

        {timeRangeType === "preset" ? (
          <>
            <div className="control-section">
              <div className="section-header">Preset Time Ranges</div>
              <div className="time-range-selector">
                <button
                  onClick={() => setPresetDays(7)}
                  className={presetDays === 7 ? "active" : ""}
                >
                  7 Days
                </button>
                <button
                  onClick={() => setPresetDays(30)}
                  className={presetDays === 30 ? "active" : ""}
                >
                  30 Days
                </button>
                <button
                  onClick={() => setPresetDays(90)}
                  className={presetDays === 90 ? "active" : ""}
                >
                  90 Days
                </button>
                <button
                  onClick={() => setPresetDays(180)}
                  className={presetDays === 180 ? "active" : ""}
                >
                  180 Days
                </button>
              </div>
            </div>

            <div className="control-section">
              <div className="section-header">Custom Days</div>
              <form
                onSubmit={handleCustomDaysSubmit}
                className="custom-days-form"
              >
                <input
                  type="number"
                  min="1"
                  max="365"
                  placeholder="Days"
                  value={customDays}
                  onChange={(e) => setCustomDays(e.target.value)}
                />
                <button type="submit">Apply</button>
              </form>
            </div>
          </>
        ) : (
          <div className="control-section">
            <div className="section-header">Custom Date Range</div>
            <div className="date-range-selector">
              <div className="date-input">
                <label>Start:</label>
                <input
                  type="date"
                  value={startDate}
                  onChange={(e) => {
                    setStartDate(e.target.value);
                    handleDateRangeChange();
                  }}
                  max={endDate}
                />
              </div>
              <div className="date-input">
                <label>End:</label>
                <input
                  type="date"
                  value={endDate}
                  onChange={(e) => {
                    setEndDate(e.target.value);
                    handleDateRangeChange();
                  }}
                  min={startDate}
                  max={new Date().toISOString().split("T")[0]}
                />
              </div>
            </div>
          </div>
        )}

        <div className="control-section">
          <div className="section-header">Data Granularity</div>
          <div className="granularity-selector">
            <button
              onClick={() => setGranularity("daily")}
              className={granularity === "daily" ? "active" : ""}
            >
              Daily
            </button>
            <button
              onClick={() => setGranularity("hourly")}
              className={granularity === "hourly" ? "active" : ""}
            >
              Hourly
            </button>
          </div>
        </div>
      </div>
    );
  }

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
        <div className="metric">
          <span className="label">Period:</span>
          <span>
            {data.length > 0 &&
              `${data[0].date} to ${data[data.length - 1].date}`}
          </span>
        </div>
      </div>

      {renderTimeControls()}

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
