import React, { useState } from "react";
import { useTradingContext } from "../context/TradingContext";
import {
  formatPrice,
  formatPnL,
  formatPnLPercentage,
  formatNumber,
} from "../utils/formatters";

type SortField =
  | "instrument"
  | "units"
  | "avgPrice"
  | "currentPrice"
  | "pnl"
  | "pnlPercent";
type SortDirection = "asc" | "desc";

const PositionsTable: React.FC = () => {
  const { positions, isLoading } = useTradingContext();
  const [sortField, setSortField] = useState<SortField>("pnl");
  const [sortDirection, setSortDirection] = useState<SortDirection>("desc");

  const handleSort = (field: SortField) => {
    if (field === sortField) {
      setSortDirection(sortDirection === "asc" ? "desc" : "asc");
    } else {
      setSortField(field);
      setSortDirection("desc");
    }
  };

  const sortedPositions = [...positions].sort((a, b) => {
    const directionMultiplier = sortDirection === "asc" ? 1 : -1;

    switch (sortField) {
      case "instrument":
        return directionMultiplier * a.instrument.localeCompare(b.instrument);
      case "units":
        return directionMultiplier * (Math.abs(a.units) - Math.abs(b.units));
      case "avgPrice":
        return directionMultiplier * (a.avgPrice - b.avgPrice);
      case "currentPrice":
        return directionMultiplier * (a.currentPrice - b.currentPrice);
      case "pnl":
        return directionMultiplier * (a.pnl - b.pnl);
      case "pnlPercent":
        return directionMultiplier * (a.pnlPercent - b.pnlPercent);
      default:
        return 0;
    }
  });

  if (isLoading && !positions.length) {
    return (
      <div className="card animate-pulse">
        <div className="h-8 bg-gray-200 rounded w-1/3 mb-4"></div>
        <div className="h-64 bg-gray-200 rounded w-full"></div>
      </div>
    );
  }

  const renderSortIcon = (field: SortField) => {
    if (field !== sortField) {
      return null;
    }

    return <span className="ml-1">{sortDirection === "asc" ? "↑" : "↓"}</span>;
  };

  return (
    <div className="card">
      <h2 className="text-lg font-semibold text-gray-800 mb-4">
        Open Positions
      </h2>

      {positions.length === 0 ? (
        <div className="text-center py-8 text-gray-500">
          No open positions found
        </div>
      ) : (
        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th
                  className="cursor-pointer hover:bg-gray-50"
                  onClick={() => handleSort("instrument")}
                >
                  Instrument {renderSortIcon("instrument")}
                </th>
                <th
                  className="cursor-pointer hover:bg-gray-50"
                  onClick={() => handleSort("units")}
                >
                  Position {renderSortIcon("units")}
                </th>
                <th
                  className="cursor-pointer hover:bg-gray-50"
                  onClick={() => handleSort("avgPrice")}
                >
                  Avg. Price {renderSortIcon("avgPrice")}
                </th>
                <th
                  className="cursor-pointer hover:bg-gray-50"
                  onClick={() => handleSort("currentPrice")}
                >
                  Current Price {renderSortIcon("currentPrice")}
                </th>
                <th
                  className="cursor-pointer hover:bg-gray-50"
                  onClick={() => handleSort("pnl")}
                >
                  P&L {renderSortIcon("pnl")}
                </th>
                <th
                  className="cursor-pointer hover:bg-gray-50"
                  onClick={() => handleSort("pnlPercent")}
                >
                  P&L % {renderSortIcon("pnlPercent")}
                </th>
              </tr>
            </thead>
            <tbody>
              {sortedPositions.map((position) => {
                const pnlFormatted = formatPnL(position.pnl);
                const pnlPercentFormatted = formatPnLPercentage(
                  position.pnlPercent
                );
                const positionType = position.units > 0 ? "LONG" : "SHORT";
                const positionClass =
                  position.units > 0 ? "text-green-600" : "text-red-600";

                return (
                  <tr key={position.instrument}>
                    <td className="font-medium">{position.instrument}</td>
                    <td>
                      <span className={positionClass}>
                        {positionType} {formatNumber(Math.abs(position.units))}
                      </span>
                    </td>
                    <td>
                      {formatPrice(position.avgPrice, position.instrument)}
                    </td>
                    <td>
                      {formatPrice(position.currentPrice, position.instrument)}
                    </td>
                    <td className={pnlFormatted.className}>
                      {pnlFormatted.value}
                    </td>
                    <td className={pnlPercentFormatted.className}>
                      {pnlPercentFormatted.value}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

export default PositionsTable;
