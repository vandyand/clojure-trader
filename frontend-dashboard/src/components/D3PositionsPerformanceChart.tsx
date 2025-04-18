import React, { useState, useEffect, useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import * as d3 from "d3";
import * as dataService from "../lib/dataService";
import { useDataSource } from "../lib/DataSourceContext";

interface D3PositionsPerformanceChartProps {
  refreshInterval?: number;
}

// Types for position data
interface PositionData {
  instrument: string;
  values: { date: Date; value: number }[];
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
const getColorForInstrument = (instrument: string) => {
  // Use hash function to generate consistent color index for each instrument
  const hash = instrument.split("").reduce((acc, char) => {
    return acc + char.charCodeAt(0);
  }, 0);
  return COLORS[hash % COLORS.length];
};

export const D3PositionsPerformanceChart: React.FC<
  D3PositionsPerformanceChartProps
> = ({
  refreshInterval = 60000 * 5, // 5 minutes default refresh
}) => {
  const { dataSource } = useDataSource();
  const [timeRange, setTimeRange] = useState(30); // Default to 30 days
  const [showDots, setShowDots] = useState(true); // Toggle for showing data points
  const svgRef = useRef<SVGSVGElement>(null);
  const tooltipRef = useRef<HTMLDivElement>(null);
  const chartContainerRef = useRef<HTMLDivElement>(null);

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

  useEffect(() => {
    if (
      isLoading ||
      error ||
      !snapshots ||
      snapshots.length === 0 ||
      !svgRef.current
    ) {
      return;
    }

    // Set up container dimensions
    const containerWidth = chartContainerRef.current?.clientWidth || 800;
    const containerHeight = 400;

    // Set margins
    const margin = { top: 20, right: 80, bottom: 30, left: 50 };
    const width = containerWidth - margin.left - margin.right;
    const height = containerHeight - margin.top - margin.bottom;

    // Clear previous charts
    d3.select(svgRef.current).selectAll("*").remove();

    // Create the SVG container
    const svg = d3
      .select(svgRef.current)
      .attr("width", containerWidth)
      .attr("height", containerHeight);

    // Create the chart group with margins
    const chart = svg
      .append("g")
      .attr("transform", `translate(${margin.left},${margin.top})`);

    // Process data - Extract and organize position data
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

    // Create a data structure for each instrument
    const positionData: PositionData[] = instruments.map((instrument) => ({
      instrument,
      values: [],
    }));

    // Process each snapshot to extract P/L for each position
    snapshots.forEach((snapshot) => {
      const date = new Date(snapshot.timestamp);

      // Initialize with 0 P/L for all instruments
      const instrumentValueMap = new Map<string, number>();
      instruments.forEach((instrument) => {
        instrumentValueMap.set(instrument, 0);
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

          instrumentValueMap.set(instrument, totalPL);
        });
      }

      // Add values to each position data
      positionData.forEach((position) => {
        const value = instrumentValueMap.get(position.instrument) || 0;
        position.values.push({ date, value });
      });
    });

    // Sort data chronologically
    positionData.forEach((position) => {
      position.values.sort((a, b) => a.date.getTime() - b.date.getTime());
    });

    // Create data for cumulative performances (average and sum of all instruments at each timestamp)
    const timestampMap = new Map<number, { total: number; count: number }>();

    // Collect all values at each timestamp
    positionData.forEach((position) => {
      position.values.forEach((dataPoint) => {
        const timestamp = dataPoint.date.getTime();
        if (!timestampMap.has(timestamp)) {
          timestampMap.set(timestamp, { total: 0, count: 0 });
        }
        const current = timestampMap.get(timestamp)!;
        current.total += dataPoint.value;
        current.count += 1;
      });
    });

    // Calculate average for each timestamp
    const cumulativeData: { date: Date; value: number }[] = [];
    // Calculate sum for each timestamp
    const sumData: { date: Date; value: number }[] = [];

    timestampMap.forEach((data, timestamp) => {
      cumulativeData.push({
        date: new Date(timestamp),
        value: data.total / data.count,
      });

      sumData.push({
        date: new Date(timestamp),
        value: data.total,
      });
    });

    // Sort by date
    cumulativeData.sort((a, b) => a.date.getTime() - b.date.getTime());
    sumData.sort((a, b) => a.date.getTime() - b.date.getTime());

    // Set up scales
    const x = d3
      .scaleTime()
      .domain(d3.extent(positionData[0].values, (d) => d.date) as [Date, Date])
      .range([0, width]);

    // Find the min and max values across all positions and cumulative data
    let minY = 0,
      maxY = 0;
    positionData.forEach((position) => {
      position.values.forEach((v) => {
        if (v.value < minY) minY = v.value;
        if (v.value > maxY) maxY = v.value;
      });
    });

    // Check cumulative data for min/max as well
    cumulativeData.forEach((v) => {
      if (v.value < minY) minY = v.value;
      if (v.value > maxY) maxY = v.value;
    });

    // Check sum data for min/max
    sumData.forEach((v) => {
      if (v.value < minY) minY = v.value;
      if (v.value > maxY) maxY = v.value;
    });

    // Add some padding to the y-axis
    const yPadding = (maxY - minY) * 0.1;

    const y = d3
      .scaleLinear()
      .domain([minY - yPadding, maxY + yPadding])
      .range([height, 0]);

    // Create a clip path to ensure content stays within the chart area
    chart
      .append("defs")
      .append("clipPath")
      .attr("id", "clip")
      .append("rect")
      .attr("width", width)
      .attr("height", height);

    // Draw axes
    const xAxis = d3
      .axisBottom(x)
      .ticks(7) // Explicit number of ticks
      .tickSize(-height) // Add gridlines across the chart
      .tickPadding(10); // Add padding between ticks and labels

    const yAxis = d3
      .axisLeft(y)
      .tickFormat((d) => `$${d3.format(".2f")(d as number)}`);

    // Add the x-axis AFTER adding content to ensure it's on top
    const chartContent = chart.append("g").attr("clip-path", "url(#clip)");

    // Now add the axes
    const xAxisGroup = chart
      .append("g")
      .attr("class", "x-axis")
      .attr("transform", `translate(0,${height})`)
      .call(xAxis);

    // Apply direct styling to the x-axis
    xAxisGroup
      .selectAll("path")
      .attr("stroke", "#666")
      .attr("stroke-width", 1.5);

    xAxisGroup
      .selectAll(".tick line")
      .attr("stroke", "#ddd")
      .attr("stroke-width", 0.5)
      .attr("opacity", 0.7);

    xAxisGroup
      .selectAll(".tick text")
      .attr("fill", "#444")
      .attr("font-size", "11px")
      .attr("font-weight", 500);

    // Add a border line at the bottom of the chart area to make x-axis more visible
    chart
      .append("line")
      .attr("x1", 0)
      .attr("y1", height)
      .attr("x2", width)
      .attr("y2", height)
      .attr("stroke", "#666")
      .attr("stroke-width", 2)
      .attr("class", "x-axis-border");

    // Add x-axis label
    chart
      .append("text")
      .attr("class", "x-axis-label")
      .attr("text-anchor", "middle")
      .attr("x", width / 2)
      .attr("y", height + margin.bottom - 2)
      .attr("fill", "#444")
      .attr("font-size", "12px")
      .attr("font-weight", 500)
      .text("Time");

    const yAxisGroup = chart.append("g").attr("class", "y-axis").call(yAxis);

    // Apply direct styling to y-axis as well
    yAxisGroup
      .selectAll("path")
      .attr("stroke", "#666")
      .attr("stroke-width", 1.5);

    // Add a zero line (horizontal line at y=0)
    const zeroLineY = y(0); // Get the pixel position for y=0

    // Only draw the zero line if it's within the visible chart area
    if (zeroLineY >= 0 && zeroLineY <= height) {
      chart
        .append("line")
        .attr("class", "zero-line")
        .attr("x1", 0)
        .attr("y1", zeroLineY)
        .attr("x2", width)
        .attr("y2", zeroLineY)
        .attr("stroke", "#444") // Changed to dark grey
        .attr("stroke-width", 1.5)
        .attr("opacity", 0.7); // Slightly reduced opacity for better integration
    }

    // Draw lines with the right definitions
    const line = d3
      .line<{ date: Date; value: number }>()
      .x((d) => x(d.date))
      .y((d) => y(d.value))
      .curve(d3.curveLinear); // Changed from d3.curveMonotoneX to d3.curveLinear for straight lines

    // Create a group for each line
    positionData.forEach((position) => {
      const color = getColorForInstrument(position.instrument);

      // Draw line
      chartContent
        .append("path")
        .datum(position.values)
        .attr("class", `line-${position.instrument.replace("_", "-")}`)
        .attr("d", line)
        .attr("fill", "none")
        .attr("stroke", color)
        .attr("stroke-width", 1.5);

      // Add invisible hover areas over line segments for tooltips when dots are hidden
      if (!showDots) {
        // Create wider transparent paths for easier hovering
        chartContent
          .append("path")
          .datum(position.values)
          .attr("class", `line-hover-${position.instrument.replace("_", "-")}`)
          .attr("d", line)
          .attr("fill", "none")
          .attr("stroke", "transparent")
          .attr("stroke-width", 10) // Wider area for easier hovering
          .style("pointer-events", "stroke") // Only trigger events on stroke, not fill
          .on("mousemove", function (event) {
            if (tooltipRef.current) {
              // Get mouse position in chart coordinates
              const [mouseX] = d3.pointer(event, this);

              // Find the closest data point to mouse position using the UPDATED scale
              const bisectDate = d3.bisector(
                (d: { date: Date }) => d.date
              ).left;
              const x0 = x.invert(mouseX);
              const i = bisectDate(position.values, x0, 1);
              const d0 = position.values[i - 1];
              const d1 = position.values[i] || d0;
              const d =
                x0.getTime() - d0.date.getTime() >
                d1.date.getTime() - x0.getTime()
                  ? d1
                  : d0;

              // Display the tooltip
              const tooltip = d3.select(tooltipRef.current);
              tooltip.style("opacity", 1);

              const displayDate = d3.timeFormat("%b %d, %Y %H:%M")(d.date);
              const formattedValue = d3.format("$,.2f")(d.value);
              const color = getColorForInstrument(position.instrument);

              tooltip.html(`
                <div class="tooltip-title" style="color: ${color};">${position.instrument.replace(
                "_",
                "/"
              )}</div>
                <div class="tooltip-date">${displayDate}</div>
                <div class="tooltip-value">P/L: ${formattedValue}</div>
              `);

              // Position the tooltip using chart container coordinates
              const tooltipWidth = tooltipRef.current.offsetWidth;
              const tooltipHeight = tooltipRef.current.offsetHeight;

              // Get the position of the chart container for correct offset calculation
              const chartRect =
                chartContainerRef.current?.getBoundingClientRect();
              if (chartRect) {
                // Calculate position relative to the chart container
                const xPosition = event.clientX - chartRect.left;
                const yPosition =
                  event.clientY - chartRect.top - tooltipHeight - 10;

                tooltip
                  .style("left", `${xPosition - tooltipWidth / 2}px`)
                  .style("top", `${yPosition}px`);
              }

              // Highlight the corresponding line
              chart
                .select(`.line-${position.instrument.replace("_", "-")}`)
                .attr("stroke-width", 3);

              // Dim other lines
              positionData.forEach((p) => {
                if (p.instrument !== position.instrument) {
                  chart
                    .select(`.line-${p.instrument.replace("_", "-")}`)
                    .attr("opacity", 0.3);
                }
              });
            }
          })
          .on("mouseout", function () {
            if (tooltipRef.current) {
              // Hide the tooltip
              d3.select(tooltipRef.current).style("opacity", 0);

              // Reset all lines
              positionData.forEach((p) => {
                chart
                  .select(`.line-${p.instrument.replace("_", "-")}`)
                  .attr("stroke-width", 1.5)
                  .attr("opacity", 1);
              });
            }
          });
      }

      // Add data points (if showDots is true)
      if (showDots) {
        chartContent
          .selectAll(`.dot-${position.instrument.replace("_", "-")}`)
          .data(position.values)
          .enter()
          .append("circle")
          .attr("class", `dot-${position.instrument.replace("_", "-")}`)
          .attr("cx", (d) => x(d.date))
          .attr("cy", (d) => y(d.value))
          .attr("r", 3)
          .attr("fill", color)
          .attr("opacity", 0.7)
          .on("mouseover", function (event, d) {
            if (tooltipRef.current) {
              // Display the tooltip
              const tooltip = d3.select(tooltipRef.current);
              tooltip.style("opacity", 1);

              const displayDate = d3.timeFormat("%b %d, %Y %H:%M")(d.date);
              const formattedValue = d3.format("$,.2f")(d.value);

              tooltip.html(`
                <div class="tooltip-title" style="color: ${color};">${position.instrument.replace(
                "_",
                "/"
              )}</div>
                <div class="tooltip-date">${displayDate}</div>
                <div class="tooltip-value">P/L: ${formattedValue}</div>
              `);

              // Position the tooltip - use chart coordinates for better accuracy
              const tooltipWidth = tooltipRef.current.offsetWidth;
              const tooltipHeight = tooltipRef.current.offsetHeight;

              // Get the position of the chart container for correct offset calculation
              const chartRect =
                chartContainerRef.current?.getBoundingClientRect();
              if (chartRect) {
                // Calculate position relative to the chart container
                const xPosition = event.clientX - chartRect.left;
                const yPosition =
                  event.clientY - chartRect.top - tooltipHeight - 10;

                tooltip
                  .style("left", `${xPosition - tooltipWidth / 2}px`)
                  .style("top", `${yPosition}px`);
              }

              // Highlight the data point
              d3.select(this)
                .transition()
                .duration(200)
                .attr("r", 6)
                .attr("opacity", 1);
            }
          })
          .on("mouseout", function () {
            if (tooltipRef.current) {
              // Hide the tooltip
              d3.select(tooltipRef.current).style("opacity", 0);

              // Reset data point size
              d3.select(this)
                .transition()
                .duration(200)
                .attr("r", 3)
                .attr("opacity", 0.7);
            }
          });
      }
    });

    // Draw cumulative performance line (average of all instruments)
    const cumulativeColor = "#000000"; // Black color for cumulative line
    const sumColor = "#000000"; // Black color for sum line

    // Draw cumulative line with thicker stroke - now solid instead of dashed
    chartContent
      .append("path")
      .datum(cumulativeData)
      .attr("class", "line-cumulative")
      .attr("d", line)
      .attr("fill", "none")
      .attr("stroke", cumulativeColor)
      .attr("stroke-width", 3);

    // Draw sum line with thicker stroke - solid
    chartContent
      .append("path")
      .datum(sumData)
      .attr("class", "line-sum")
      .attr("d", line)
      .attr("fill", "none")
      .attr("stroke", sumColor)
      .attr("stroke-width", 3);

    // Add data points for cumulative line if showDots is true
    if (showDots) {
      chartContent
        .selectAll(".dot-cumulative")
        .data(cumulativeData)
        .enter()
        .append("circle")
        .attr("class", "dot-cumulative")
        .attr("cx", (d) => x(d.date))
        .attr("cy", (d) => y(d.value))
        .attr("r", 4) // Slightly larger dots for the cumulative line
        .attr("fill", cumulativeColor)
        .attr("opacity", 0.8)
        .on("mouseover", function (event, d) {
          if (tooltipRef.current) {
            // Display the tooltip
            const tooltip = d3.select(tooltipRef.current);
            tooltip.style("opacity", 1);

            const displayDate = d3.timeFormat("%b %d, %Y %H:%M")(d.date);
            const formattedValue = d3.format("$,.2f")(d.value);

            tooltip.html(`
              <div class="tooltip-title" style="color: ${cumulativeColor};">Average Performance</div>
              <div class="tooltip-date">${displayDate}</div>
              <div class="tooltip-value">P/L: ${formattedValue}</div>
            `);

            // Position the tooltip using chart container coordinates
            const tooltipWidth = tooltipRef.current.offsetWidth;
            const tooltipHeight = tooltipRef.current.offsetHeight;

            // Get the position of the chart container for correct offset calculation
            const chartRect =
              chartContainerRef.current?.getBoundingClientRect();
            if (chartRect) {
              // Calculate position relative to the chart container
              const xPosition = event.clientX - chartRect.left;
              const yPosition =
                event.clientY - chartRect.top - tooltipHeight - 10;

              tooltip
                .style("left", `${xPosition - tooltipWidth / 2}px`)
                .style("top", `${yPosition}px`);
            }

            // Highlight the data point
            d3.select(this)
              .transition()
              .duration(200)
              .attr("r", 7)
              .attr("opacity", 1);
          }
        })
        .on("mouseout", function () {
          if (tooltipRef.current) {
            // Hide the tooltip
            d3.select(tooltipRef.current).style("opacity", 0);

            // Reset data point size
            d3.select(this)
              .transition()
              .duration(200)
              .attr("r", 4)
              .attr("opacity", 0.8);
          }
        });

      // Add data points for sum line
      chartContent
        .selectAll(".dot-sum")
        .data(sumData)
        .enter()
        .append("circle")
        .attr("class", "dot-sum")
        .attr("cx", (d) => x(d.date))
        .attr("cy", (d) => y(d.value))
        .attr("r", 4) // Slightly larger dots for the sum line
        .attr("fill", sumColor)
        .attr("opacity", 0.8)
        .on("mouseover", function (event, d) {
          if (tooltipRef.current) {
            // Display the tooltip
            const tooltip = d3.select(tooltipRef.current);
            tooltip.style("opacity", 1);

            const displayDate = d3.timeFormat("%b %d, %Y %H:%M")(d.date);
            const formattedValue = d3.format("$,.2f")(d.value);

            tooltip.html(`
              <div class="tooltip-title" style="color: ${sumColor};">Total Performance</div>
              <div class="tooltip-date">${displayDate}</div>
              <div class="tooltip-value">P/L: ${formattedValue}</div>
            `);

            // Position the tooltip using chart container coordinates
            const tooltipWidth = tooltipRef.current.offsetWidth;
            const tooltipHeight = tooltipRef.current.offsetHeight;

            // Get the position of the chart container for correct offset calculation
            const chartRect =
              chartContainerRef.current?.getBoundingClientRect();
            if (chartRect) {
              // Calculate position relative to the chart container
              const xPosition = event.clientX - chartRect.left;
              const yPosition =
                event.clientY - chartRect.top - tooltipHeight - 10;

              tooltip
                .style("left", `${xPosition - tooltipWidth / 2}px`)
                .style("top", `${yPosition}px`);
            }

            // Highlight the data point
            d3.select(this)
              .transition()
              .duration(200)
              .attr("r", 7)
              .attr("opacity", 1);
          }
        })
        .on("mouseout", function () {
          if (tooltipRef.current) {
            // Hide the tooltip
            d3.select(tooltipRef.current).style("opacity", 0);

            // Reset data point size
            d3.select(this)
              .transition()
              .duration(200)
              .attr("r", 4)
              .attr("opacity", 0.8);
          }
        });
    }

    // Add legend
    const legend = svg
      .append("g")
      .attr("class", "legend")
      .attr(
        "transform",
        `translate(${width + margin.left + 10}, ${margin.top})`
      );

    // Add cumulative entry to the legend (at the top)
    const cumulativeLegendItem = legend
      .append("g")
      .attr("transform", `translate(0, 0)`);

    cumulativeLegendItem
      .append("rect")
      .attr("width", 10)
      .attr("height", 10)
      .attr("fill", cumulativeColor);

    cumulativeLegendItem
      .append("line")
      .attr("x1", 0)
      .attr("y1", 5)
      .attr("x2", 10)
      .attr("y2", 5)
      .attr("stroke", cumulativeColor)
      .attr("stroke-width", 3);

    cumulativeLegendItem
      .append("text")
      .attr("x", 15)
      .attr("y", 10)
      .text("Average Performance")
      .style("font-size", "12px")
      .style("font-weight", "bold");

    // Add sum entry to the legend (below the average entry)
    const sumLegendItem = legend
      .append("g")
      .attr("transform", `translate(0, 20)`);

    sumLegendItem
      .append("rect")
      .attr("width", 10)
      .attr("height", 10)
      .attr("fill", sumColor);

    sumLegendItem
      .append("line")
      .attr("x1", 0)
      .attr("y1", 5)
      .attr("x2", 10)
      .attr("y2", 5)
      .attr("stroke", sumColor)
      .attr("stroke-width", 3);

    sumLegendItem
      .append("text")
      .attr("x", 15)
      .attr("y", 10)
      .text("Total Performance")
      .style("font-size", "12px")
      .style("font-weight", "bold");

    // Add hover interaction with the cumulative legend
    cumulativeLegendItem
      .style("cursor", "pointer")
      .on("mouseover", function () {
        // Highlight cumulative line
        chart.select(".line-cumulative").attr("stroke-width", 5);

        // Dim individual lines and sum line
        chart.select(".line-sum").attr("opacity", 0.3);
        positionData.forEach((p) => {
          chart
            .select(`.line-${p.instrument.replace("_", "-")}`)
            .attr("opacity", 0.3);
        });
      })
      .on("mouseout", function () {
        // Reset all lines
        chart.select(".line-cumulative").attr("stroke-width", 3);
        chart.select(".line-sum").attr("opacity", 1);

        positionData.forEach((p) => {
          chart
            .select(`.line-${p.instrument.replace("_", "-")}`)
            .attr("opacity", 1);
        });
      });

    // Add hover interaction with the sum legend
    sumLegendItem
      .style("cursor", "pointer")
      .on("mouseover", function () {
        // Highlight sum line
        chart.select(".line-sum").attr("stroke-width", 5);

        // Dim individual lines and cumulative line
        chart.select(".line-cumulative").attr("opacity", 0.3);
        positionData.forEach((p) => {
          chart
            .select(`.line-${p.instrument.replace("_", "-")}`)
            .attr("opacity", 0.3);
        });
      })
      .on("mouseout", function () {
        // Reset all lines
        chart.select(".line-sum").attr("stroke-width", 3);
        chart.select(".line-cumulative").attr("opacity", 1);

        positionData.forEach((p) => {
          chart
            .select(`.line-${p.instrument.replace("_", "-")}`)
            .attr("opacity", 1);
        });
      });

    // Add individual instrument entries to the legend (after the cumulative entry)
    positionData.forEach((position, i) => {
      const legendItem = legend
        .append("g")
        .attr("transform", `translate(0, ${(i + 2) * 20})`); // +2 to account for cumulative and sum legend items

      legendItem
        .append("rect")
        .attr("width", 10)
        .attr("height", 10)
        .attr("fill", getColorForInstrument(position.instrument));

      legendItem
        .append("text")
        .attr("x", 15)
        .attr("y", 10)
        .text(position.instrument.replace("_", "/"))
        .style("font-size", "12px");
    });

    // Add zoom behavior with both X and Y axis support
    const zoom = d3
      .zoom<SVGSVGElement, unknown>()
      .scaleExtent([1, 20])
      .extent([
        [0, 0],
        [width, height],
      ])
      .on("zoom", (event) => {
        // Get the new scales from the transform event
        const newX = event.transform.rescaleX(x);
        const newY = event.transform.rescaleY(y);

        // Update x-axis with more detailed styling to ensure visibility
        xAxisGroup.call((g) => {
          const updatedXAxis = d3
            .axisBottom(newX)
            .ticks(7)
            .tickSize(-height)
            .tickPadding(10);
          g.call(updatedXAxis);

          // Reapply styling to ensure x-axis remains properly styled
          g.selectAll("path").attr("stroke", "#666").attr("stroke-width", 1.5);

          g.selectAll(".tick line")
            .attr("stroke", "#ddd")
            .attr("stroke-width", 0.5)
            .attr("opacity", 0.7);

          g.selectAll(".tick text")
            .attr("fill", "#444")
            .attr("font-size", "11px")
            .attr("font-weight", 500);
        });

        // Update y-axis
        yAxisGroup.call((g) => {
          const updatedYAxis = d3
            .axisLeft(newY)
            .tickFormat((d) => `$${d3.format(".2f")(d as number)}`);
          g.call(updatedYAxis);

          // Reapply styling to y-axis
          g.selectAll("path").attr("stroke", "#666").attr("stroke-width", 1.5);
        });

        // Also update the bottom border line
        chart.select(".x-axis-border").attr("y1", height).attr("y2", height);

        // Update the zero line position if it exists
        if (chart.select(".zero-line").size() > 0) {
          const newZeroLineY = newY(0);

          // Only show the zero line if it's within the visible area after zooming
          if (newZeroLineY >= 0 && newZeroLineY <= height) {
            chart
              .select(".zero-line")
              .attr("y1", newZeroLineY)
              .attr("y2", newZeroLineY)
              .style("display", "block");
          } else {
            // Hide the zero line if it's outside the visible area
            chart.select(".zero-line").style("display", "none");
          }
        }

        // Update line positions with both new X and new Y scales
        positionData.forEach((position) => {
          const updatedLine = d3
            .line<{ date: Date; value: number }>()
            .x((d) => newX(d.date))
            .y((d) => newY(d.value))
            .curve(d3.curveLinear); // Changed from d3.curveMonotoneX to d3.curveLinear for straight lines

          chart
            .select(`.line-${position.instrument.replace("_", "-")}`)
            .attr("d", updatedLine(position.values));

          // Update the invisible hover areas for each line
          if (!showDots) {
            const lineHover = chart.select(
              `.line-hover-${position.instrument.replace("_", "-")}`
            );

            lineHover.attr("d", updatedLine(position.values));

            // Update the mousemove event handler to use new scales
            lineHover.on("mousemove", function (event) {
              if (tooltipRef.current) {
                // Get mouse position in chart coordinates
                const [mouseX] = d3.pointer(event, this);

                // Find the closest data point to mouse position using the UPDATED scale
                const bisectDate = d3.bisector(
                  (d: { date: Date }) => d.date
                ).left;
                const x0 = newX.invert(mouseX); // Use newX instead of x
                const i = bisectDate(position.values, x0, 1);
                const d0 = position.values[i - 1];
                const d1 = position.values[i] || d0;
                const d =
                  x0.getTime() - d0.date.getTime() >
                  d1.date.getTime() - x0.getTime()
                    ? d1
                    : d0;

                // Display the tooltip
                const tooltip = d3.select(tooltipRef.current);
                tooltip.style("opacity", 1);

                const displayDate = d3.timeFormat("%b %d, %Y %H:%M")(d.date);
                const formattedValue = d3.format("$,.2f")(d.value);
                const color = getColorForInstrument(position.instrument);

                tooltip.html(`
                    <div class="tooltip-title" style="color: ${color};">${position.instrument.replace(
                  "_",
                  "/"
                )}</div>
                    <div class="tooltip-date">${displayDate}</div>
                    <div class="tooltip-value">P/L: ${formattedValue}</div>
                  `);

                // Position the tooltip using chart container coordinates
                const tooltipWidth = tooltipRef.current.offsetWidth;
                const tooltipHeight = tooltipRef.current.offsetHeight;

                // Get the position of the chart container for correct offset calculation
                const chartRect =
                  chartContainerRef.current?.getBoundingClientRect();
                if (chartRect) {
                  // Calculate position relative to the chart container
                  const xPosition = event.clientX - chartRect.left;
                  const yPosition =
                    event.clientY - chartRect.top - tooltipHeight - 10;

                  tooltip
                    .style("left", `${xPosition - tooltipWidth / 2}px`)
                    .style("top", `${yPosition}px`);
                }

                // Highlight the corresponding line
                chart
                  .select(`.line-${position.instrument.replace("_", "-")}`)
                  .attr("stroke-width", 3);

                // Dim other lines
                positionData.forEach((p) => {
                  if (p.instrument !== position.instrument) {
                    chart
                      .select(`.line-${p.instrument.replace("_", "-")}`)
                      .attr("opacity", 0.3);
                  }
                });
              }
            });
          }

          // Update data points if they're visible
          if (showDots) {
            chart
              .selectAll(`.dot-${position.instrument.replace("_", "-")}`)
              .attr("cx", (d) => newX((d as any).date))
              .attr("cy", (d) => newY((d as any).value));
          }
        });

        // Update cumulative line
        const updatedCumulativeLine = d3
          .line<{ date: Date; value: number }>()
          .x((d) => newX(d.date))
          .y((d) => newY(d.value))
          .curve(d3.curveLinear);

        chart
          .select(".line-cumulative")
          .attr("d", updatedCumulativeLine(cumulativeData));

        // Update sum line
        chart.select(".line-sum").attr("d", updatedCumulativeLine(sumData));

        // Update cumulative data points if they're visible
        if (showDots) {
          chart
            .selectAll(".dot-cumulative")
            .attr("cx", (d) => newX((d as any).date))
            .attr("cy", (d) => newY((d as any).value));

          // Update sum data points
          chart
            .selectAll(".dot-sum")
            .attr("cx", (d) => newX((d as any).date))
            .attr("cy", (d) => newY((d as any).value));
        }
      });

    // Apply zoom behavior to chart area
    svg.call(zoom);

    // Add reset zoom button functionality
    d3.select(".reset-zoom-button").on("click", function () {
      svg.transition().duration(750).call(zoom.transform, d3.zoomIdentity);
    });
  }, [snapshots, isLoading, error, timeRange, showDots]);

  // Toggle dots visibility
  const handleToggleDots = () => {
    setShowDots(!showDots);
  };

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

  return (
    <div className="positions-performance-chart">
      <h2>Positions Performance</h2>

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
            <button className="reset-zoom-button">Reset Zoom</button>
          </div>
        </div>

        <div className="control-section">
          <div className="section-header">Display Options</div>
          <div className="display-options">
            <label className="toggle-switch">
              <input
                type="checkbox"
                checked={showDots}
                onChange={handleToggleDots}
              />
              <span className="toggle-slider"></span>
              <span className="toggle-label">Show Data Points</span>
            </label>
          </div>
        </div>
      </div>

      <div
        className="chart-container"
        ref={chartContainerRef}
        style={{ width: "100%", height: 400 }}
      >
        <svg ref={svgRef}></svg>
        <div
          ref={tooltipRef}
          className="d3-tooltip"
          style={{
            opacity: 0,
            position: "absolute",
            pointerEvents: "none",
            backgroundColor: "rgba(255, 255, 255, 0.95)",
            padding: "10px",
            borderRadius: "4px",
            boxShadow: "0 2px 8px rgba(0,0,0,0.2)",
            fontSize: "12px",
            zIndex: 100,
            border: "1px solid #ddd",
            minWidth: "150px",
            textAlign: "center",
          }}
        ></div>
      </div>
      <div className="chart-instructions">
        <p>
          Use mouse wheel to zoom in/out in both dimensions, drag to pan the
          chart, hover over points for details
        </p>
      </div>
    </div>
  );
};
