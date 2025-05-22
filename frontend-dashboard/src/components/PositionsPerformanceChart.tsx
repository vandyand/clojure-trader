import React, { useState, useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceArea,
} from "recharts";
import { format } from "date-fns";
import * as dataService from "../lib/dataService";
import { useDataSource } from "../lib/DataSourceContext";

interface PositionsPerformanceChartProps {
  refreshInterval?: number;
}

// Types for processed position data
interface PositionPerformanceData {
  timestamp: string;
  formattedDate: string;
  [key: string]: string | number; // Dynamic keys for each position's P/L
}

// Extended color palette with more unique colors
const COLORS = [
  "#2451B7", // Blue
  "#E67E22", // Orange
  "#27AE60", // Green
  "#E74C3C", // Red
  "#9B59B6", // Purple
  "#16A085", // Teal
  "#F1C40F", // Yellow
  "#34495E", // Dark blue
  "#D35400", // Dark orange
  "#2ECC71", // Light green
  "#8E44AD", // Dark purple
  "#2980B9", // Light blue
  "#E84393", // Pink
  "#6D214F", // Burgundy
  "#FD79A8", // Light pink
  "#00CEC9", // Cyan
  "#55EFC4", // Mint
  "#FFC312", // Mustard
  "#C0392B", // Dark red
  "#7F8C8D", // Gray
  "#1ABC9C", // Turquoise
  "#9C27B0", // Deep purple
  "#3F51B5", // Indigo
  "#795548", // Brown
  "#607D8B", // Blue gray
];

// Function to generate unique color for each instrument
const getColorForInstrument = (instrument: string, index: number) => {
  // Use hash function to generate consistent color index for each instrument
  const hash = instrument.split("").reduce((acc, char) => {
    return acc + char.charCodeAt(0);
  }, 0);
  return COLORS[hash % COLORS.length];
};

export const PositionsPerformanceChart: React.FC<
  PositionsPerformanceChartProps
> = ({
  refreshInterval = 60000 * 5, // 5 minutes default refresh
}) => {
  const { dataSource } = useDataSource();
  const [timeRange, setTimeRange] = useState(30); // Default to 30 days

  // States for zoom functionality
  const [left, setLeft] = useState<string | number | undefined>(undefined);
  const [right, setRight] = useState<string | number | undefined>(undefined);
  const [refAreaLeft, setRefAreaLeft] = useState<string | undefined>(undefined);
  const [refAreaRight, setRefAreaRight] = useState<string | undefined>(
    undefined
  );
  const [top, setTop] = useState<number | "auto" | undefined>(undefined);
  const [bottom, setBottom] = useState<number | "auto" | undefined>(undefined);

  // For tooltip positioning
  const chartRef = useRef<any>(null);

  // Fetch account snapshots with positions data
  const {
    data: snapshots,
    isLoading,
    error,
  } = useQuery({
    queryKey: ["accountSnapshots", timeRange, dataSource],
    queryFn: () =>
      dataService.getAccountHistory(
        timeRange,
        undefined,
        undefined,
        dataSource
      ),
    refetchInterval: refreshInterval,
  });

  if (isLoading) return <div>Loading positions performance data...</div>;
  if (error) return <div>Error loading positions performance data</div>;
  if (!snapshots || snapshots.length === 0) {
    return (
      <div className="positions-performance-chart empty">
        <h2>Positions Performance</h2>
        <p>
          No positions data available. Data will be collected as you use the
          dashboard.
        </p>
        <div className="time-controls">
          <div className="control-section">
            <div className="section-header">Time Range</div>
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
        </div>
      </div>
    );
  }

  // Process snapshots to extract positions data
  const processedData: PositionPerformanceData[] = [];
  const instrumentSet = new Set<string>();

  // First, identify all unique instruments across all snapshots
  snapshots.forEach((snapshot) => {
    if (snapshot.positions && snapshot.positions.length > 0) {
      snapshot.positions.forEach((position) => {
        instrumentSet.add(position.instrument);
      });
    }
  });

  // Convert Set to Array for easier handling
  const instruments = Array.from(instrumentSet);

  // Process each snapshot to extract P/L for each position
  snapshots.forEach((snapshot) => {
    const dataPoint: PositionPerformanceData = {
      timestamp: snapshot.timestamp,
      formattedDate: format(new Date(snapshot.timestamp), "MMM dd HH:mm"),
    };

    // Initialize all instruments with 0 P/L
    instruments.forEach((instrument) => {
      dataPoint[instrument] = 0;
    });

    // Update P/L values for positions that exist in this snapshot
    if (snapshot.positions && snapshot.positions.length > 0) {
      snapshot.positions.forEach((position) => {
        const instrument = position.instrument;
        let totalPL = 0;

        // Sum up P/L from both long and short positions if they exist
        if (position.long && position.long.units !== "0") {
          totalPL += parseFloat(position.long.unrealizedPL || "0");
        }
        if (position.short && position.short.units !== "0") {
          totalPL += parseFloat(position.short.unrealizedPL || "0");
        }

        dataPoint[instrument] = totalPL;
      });
    }

    processedData.push(dataPoint);
  });

  // Sort data chronologically
  processedData.sort(
    (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
  );

  // Zoom related handlers
  const zoomIn = () => {
    if (refAreaLeft === refAreaRight || refAreaRight === undefined) {
      setRefAreaLeft(undefined);
      setRefAreaRight(undefined);
      return;
    }

    // xAxis domain
    let leftIndex = processedData.findIndex(
      (item) => item.formattedDate === refAreaLeft
    );
    let rightIndex = processedData.findIndex(
      (item) => item.formattedDate === refAreaRight
    );

    if (leftIndex > rightIndex) {
      [leftIndex, rightIndex] = [rightIndex, leftIndex];
    }

    // yAxis domain
    const yValues = processedData
      .slice(leftIndex, rightIndex + 1)
      .flatMap((item) =>
        instruments.map((instrument) => Number(item[instrument]))
      );
    const [minY, maxY] = [Math.min(...yValues), Math.max(...yValues)];

    setLeft(leftIndex);
    setRight(rightIndex);
    setBottom(minY);
    setTop(maxY);
    setRefAreaLeft(undefined);
    setRefAreaRight(undefined);
  };

  const zoomOut = () => {
    setLeft(undefined);
    setRight(undefined);
    setTop(undefined);
    setBottom(undefined);
    setRefAreaLeft(undefined);
    setRefAreaRight(undefined);
  };

  const displayFormatDate = (date: string) => {
    return date;
  };

  const getAxisYDomain = (
    from: number,
    to: number,
    ref: string,
    offset: number
  ) => {
    const refData = processedData.slice(from - 1, to);
    let [bottom, top] = [
      refData[0][ref],
      refData[0][ref],
    ] as unknown as number[];

    refData.forEach((d) => {
      if (d[ref] > top) top = d[ref] as number;
      if (d[ref] < bottom) bottom = d[ref] as number;
    });

    return [(bottom | 0) - offset, (top | 0) + offset];
  };

  return (
    <div className="positions-performance-chart">
      <h2>Positions Performance</h2>

      <div className="time-controls">
        <div className="control-section">
          <div className="section-header">Time Range</div>
          <div className="time-range-selector">
            <button
              onClick={() => {
                setTimeRange(7);
                zoomOut();
              }}
              className={timeRange === 7 ? "active" : ""}
            >
              7 Days
            </button>
            <button
              onClick={() => {
                setTimeRange(30);
                zoomOut();
              }}
              className={timeRange === 30 ? "active" : ""}
            >
              30 Days
            </button>
            <button
              onClick={() => {
                setTimeRange(90);
                zoomOut();
              }}
              className={timeRange === 90 ? "active" : ""}
            >
              90 Days
            </button>
            {(left !== undefined || right !== undefined) && (
              <button className="reset-zoom-button" onClick={zoomOut}>
                Reset Zoom
              </button>
            )}
          </div>
        </div>
      </div>

      <div className="chart-container" style={{ width: "100%", height: 400 }}>
        <ResponsiveContainer>
          <LineChart
            ref={chartRef}
            data={processedData}
            margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
            onMouseDown={(e) => {
              if (!e) return;
              setRefAreaLeft(e.activeLabel);
            }}
            onMouseMove={(e) => {
              if (!e) return;
              refAreaLeft && setRefAreaRight(e.activeLabel);
            }}
            onMouseUp={zoomIn}
          >
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis
              dataKey="formattedDate"
              allowDataOverflow
              tickFormatter={displayFormatDate}
              domain={[
                left === undefined ? "dataMin" : left,
                right === undefined ? "dataMax" : right,
              ]}
              type="category"
            />
            <YAxis
              allowDataOverflow
              domain={[
                bottom === undefined ? "auto" : bottom,
                top === undefined ? "auto" : top,
              ]}
              tickFormatter={(value) => `$${value.toFixed(2)}`}
            />
            <Tooltip
              formatter={(value) => [`$${Number(value).toFixed(2)}`, "P/L"]}
              labelFormatter={(value) => `Date: ${value}`}
            />
            <Legend />
            {instruments.map((instrument, index) => (
              <Line
                key={instrument}
                type="monotone"
                dataKey={instrument}
                name={instrument.replace("_", "/")}
                stroke={getColorForInstrument(instrument, index)}
                activeDot={{ r: 6 }}
                dot={{ r: 2 }}
              />
            ))}
            {refAreaLeft && refAreaRight && (
              <ReferenceArea
                x1={refAreaLeft}
                x2={refAreaRight}
                strokeOpacity={0.3}
                fill="#2451B7"
                fillOpacity={0.1}
              />
            )}
          </LineChart>
        </ResponsiveContainer>
      </div>
      <div className="chart-instructions">
        <p>
          Drag to zoom in on a specific area. Click "Reset Zoom" to zoom out.
        </p>
      </div>
    </div>
  );
};
