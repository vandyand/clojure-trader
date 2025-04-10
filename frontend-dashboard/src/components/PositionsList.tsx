import React from "react";
import { useQuery } from "@tanstack/react-query";
import * as oandaApi from "../lib/oanda";

interface PositionsListProps {
  refreshInterval?: number;
}

interface PositionsData {
  positions: Array<{
    instrument: string;
    long: {
      units: string;
      averagePrice: string;
      unrealizedPL: string;
    };
    short: {
      units: string;
      averagePrice: string;
      unrealizedPL: string;
    };
    currentPrice?: string;
  }>;
}

export const PositionsList: React.FC<PositionsListProps> = ({
  refreshInterval = 60000, // 1 minute default refresh
}) => {
  const { data, isLoading, error } = useQuery({
    queryKey: ["openPositions"],
    queryFn: oandaApi.getOpenPositions,
    refetchInterval: refreshInterval,
  });

  if (isLoading) return <div>Loading positions...</div>;
  if (error) return <div>Error loading positions</div>;
  if (!data || !data.positions || data.positions.length === 0) {
    return <div className="positions-list empty">No open positions</div>;
  }

  return (
    <div className="positions-list">
      <h2>Open Positions</h2>
      <table>
        <thead>
          <tr>
            <th>Instrument</th>
            <th>Units</th>
            <th>Avg. Price</th>
            <th>Current Price</th>
            <th>Unrealized P/L</th>
          </tr>
        </thead>
        <tbody>
          {data.positions.map((position) => {
            const { instrument, long, short } = position;
            const hasLong = long.units !== "0";
            const hasShort = short.units !== "0";

            return (
              <React.Fragment key={instrument}>
                {hasLong && (
                  <tr className="position-row long">
                    <td>{instrument}</td>
                    <td className="positive">
                      {parseFloat(long.units).toFixed(0)}
                    </td>
                    <td>{parseFloat(long.averagePrice).toFixed(5)}</td>
                    <td>{position.currentPrice || "N/A"}</td>
                    <td
                      className={
                        parseFloat(long.unrealizedPL) >= 0
                          ? "positive"
                          : "negative"
                      }
                    >
                      ${parseFloat(long.unrealizedPL).toFixed(2)}
                    </td>
                  </tr>
                )}
                {hasShort && (
                  <tr className="position-row short">
                    <td>{instrument}</td>
                    <td className="negative">
                      {parseFloat(short.units).toFixed(0)}
                    </td>
                    <td>{parseFloat(short.averagePrice).toFixed(5)}</td>
                    <td>{position.currentPrice || "N/A"}</td>
                    <td
                      className={
                        parseFloat(short.unrealizedPL) >= 0
                          ? "positive"
                          : "negative"
                      }
                    >
                      ${parseFloat(short.unrealizedPL).toFixed(2)}
                    </td>
                  </tr>
                )}
              </React.Fragment>
            );
          })}
        </tbody>
      </table>
    </div>
  );
};
