import React, { useState, useEffect } from "react";
import {
  BacktestResult,
  BacktestDetail as BacktestDetailType,
  BacktestPositionScore,
} from "../api/tradingService";
import { useTradingContext } from "../context/TradingContext";
import oandaApiService from "../api/oandaApiClient";
import { format } from "date-fns";

interface BacktestDetailProps {
  backtestId: string;
  onClose: () => void;
}

const BacktestDetail: React.FC<BacktestDetailProps> = ({
  backtestId,
  onClose,
}) => {
  const [backtest, setBacktest] = useState<BacktestDetailType | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [executeAmount, setExecuteAmount] = useState<string>("25");
  const [isExecuting, setIsExecuting] = useState<boolean>(false);

  useEffect(() => {
    const fetchBacktestDetail = async () => {
      try {
        setLoading(true);
        const data = await oandaApiService.getBacktestById(backtestId);
        setBacktest(data);
      } catch (error) {
        console.error("Error fetching backtest details:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchBacktestDetail();
  }, [backtestId]);

  const handleExecuteBacktest = async () => {
    if (!backtest) return;

    try {
      setIsExecuting(true);
      const amount = parseFloat(executeAmount);
      if (isNaN(amount) || amount <= 0) {
        alert("Please enter a valid amount");
        return;
      }

      await oandaApiService.executeBacktestPositions(backtest.id, amount);
      alert(`Successfully executed backtest positions with $${amount}`);
      onClose();
    } catch (error) {
      console.error("Error executing backtest positions:", error);
      alert("Failed to execute backtest positions. See console for details.");
    } finally {
      setIsExecuting(false);
    }
  };

  if (loading) {
    return (
      <div className="fixed inset-0 bg-gray-600 bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white rounded-lg shadow-lg p-8">
          <div className="flex items-center justify-center">
            <svg
              className="animate-spin h-8 w-8 text-blue-600 mr-3"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
            >
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              ></circle>
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
              ></path>
            </svg>
            <span className="text-gray-700">Loading backtest details...</span>
          </div>
        </div>
      </div>
    );
  }

  if (!backtest) {
    return (
      <div className="fixed inset-0 bg-gray-600 bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white rounded-lg shadow-lg p-8">
          <div className="text-red-600 mb-4">
            Error loading backtest details
          </div>
          <div className="flex justify-end">
            <button onClick={onClose} className="btn-secondary">
              Close
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 bg-gray-600 bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-lg w-full max-w-4xl overflow-hidden">
        <div className="flex justify-between items-center p-4 border-b">
          <h2 className="text-xl font-semibold">
            Backtest Details: {backtest.id}
          </h2>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700"
          >
            <svg
              className="w-6 h-6"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              xmlns="http://www.w3.org/2000/svg"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        <div className="p-6">
          <div className="grid grid-cols-2 gap-6 mb-6">
            <div>
              <h3 className="text-sm font-medium text-gray-500 mb-1">
                Date Range
              </h3>
              <p className="text-gray-800">
                {backtest.startDate} to {backtest.endDate}
              </p>
            </div>
            <div>
              <h3 className="text-sm font-medium text-gray-500 mb-1">
                Timeframe
              </h3>
              <p className="text-gray-800">{backtest.timeframe}</p>
            </div>
            <div>
              <h3 className="text-sm font-medium text-gray-500 mb-1">
                Performance
              </h3>
              <p
                className={`text-lg font-medium ${
                  backtest.performance >= 0 ? "text-green-600" : "text-red-600"
                }`}
              >
                {backtest.performance >= 0 ? "+" : ""}
                {backtest.performance.toFixed(2)}%
              </p>
            </div>
            <div>
              <h3 className="text-sm font-medium text-gray-500 mb-1">
                Sharpe Ratio
              </h3>
              <p className="text-lg font-medium">
                {backtest.sharpeRatio.toFixed(2)}
              </p>
            </div>
            <div>
              <h3 className="text-sm font-medium text-gray-500 mb-1">
                Max Drawdown
              </h3>
              <p className="text-lg font-medium text-red-600">
                -{backtest.maxDrawdown.toFixed(2)}%
              </p>
            </div>
            <div>
              <h3 className="text-sm font-medium text-gray-500 mb-1">
                Win Rate
              </h3>
              <p className="text-lg font-medium">
                {backtest.winRate.toFixed(2)}% ({backtest.trades} trades)
              </p>
            </div>
          </div>

          <div className="mb-6">
            <h3 className="text-sm font-medium text-gray-500 mb-2">
              Instruments
            </h3>
            <div className="flex flex-wrap gap-2">
              {backtest.instruments.map((instrument) => (
                <span
                  key={instrument}
                  className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm"
                >
                  {instrument}
                </span>
              ))}
            </div>
          </div>

          {/* Position Scores Table */}
          <div className="mt-6">
            <h3 className="text-sm font-medium text-gray-500 mb-2">
              Position Scores
            </h3>
            <div className="table-container">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Instrument</th>
                    <th>Buy/Sell Score</th>
                    <th>Target Position</th>
                    <th>Latest Price</th>
                    <th>USD Amount</th>
                  </tr>
                </thead>
                <tbody>
                  {backtest.positionScores.map((score) => (
                    <tr key={score.instrument}>
                      <td>{score.instrument}</td>
                      <td
                        className={score.relBuySellScore >= 0 ? "gain" : "loss"}
                      >
                        {score.relBuySellScore.toFixed(2)}
                      </td>
                      <td
                        className={score.targetPosition >= 0 ? "gain" : "loss"}
                      >
                        {score.targetPosition.toLocaleString()}
                      </td>
                      <td>{score.latestPrice.toFixed(5)}</td>
                      <td
                        className={
                          score.usdBuySellAmount && score.usdBuySellAmount >= 0
                            ? "gain"
                            : "loss"
                        }
                      >
                        $
                        {score.usdBuySellAmount
                          ? Math.abs(score.usdBuySellAmount).toFixed(2)
                          : "-"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="pt-4 border-t mt-6">
            <h3 className="text-sm font-medium text-gray-500 mb-2">
              Strategy Analysis
            </h3>
            <p className="text-sm text-gray-600 mb-4">
              This backtest used genetic algorithm optimization to find the
              optimal parameters for the trading strategy. The strategy was
              evaluated on {backtest.trades} trades over the test period,
              achieving a {backtest.winRate.toFixed(2)}% win rate and a Sharpe
              ratio of {backtest.sharpeRatio.toFixed(2)}.
            </p>

            <div className="bg-gray-50 p-4 rounded-md">
              <h4 className="font-medium text-gray-700 mb-2">Key Insights</h4>
              <ul className="text-sm text-gray-600 list-disc pl-5 space-y-1">
                <li>
                  Performance shows{" "}
                  {backtest.performance >= 5
                    ? "strong"
                    : backtest.performance >= 0
                    ? "moderate"
                    : "weak"}{" "}
                  profitability
                </li>
                <li>
                  Sharpe ratio is{" "}
                  {backtest.sharpeRatio >= 1.5
                    ? "excellent"
                    : backtest.sharpeRatio >= 1
                    ? "good"
                    : "below optimal"}
                </li>
                <li>
                  Maximum drawdown is{" "}
                  {backtest.maxDrawdown <= 5
                    ? "well-contained"
                    : backtest.maxDrawdown <= 10
                    ? "moderate"
                    : "significant"}
                </li>
                <li>
                  Win rate is{" "}
                  {backtest.winRate >= 60
                    ? "above average"
                    : backtest.winRate >= 50
                    ? "average"
                    : "below average"}
                </li>
              </ul>
            </div>
          </div>
        </div>

        <div className="bg-gray-50 p-4 border-t flex justify-between">
          <div className="flex items-center">
            <label
              htmlFor="executeAmount"
              className="mr-2 text-sm text-gray-700"
            >
              Execution Amount ($):
            </label>
            <input
              id="executeAmount"
              type="number"
              min="0"
              step="5"
              value={executeAmount}
              onChange={(e) => setExecuteAmount(e.target.value)}
              className="w-24 px-2 py-1 border rounded-md"
            />
          </div>

          <div>
            <button onClick={onClose} className="btn-secondary mr-2">
              Close
            </button>
            <button
              className="btn-primary"
              onClick={handleExecuteBacktest}
              disabled={isExecuting}
            >
              {isExecuting ? (
                <>
                  <svg
                    className="animate-spin -ml-1 mr-2 h-4 w-4 text-white"
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                  >
                    <circle
                      className="opacity-25"
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      strokeWidth="4"
                    ></circle>
                    <path
                      className="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                    ></path>
                  </svg>
                  Executing...
                </>
              ) : (
                "Execute Positions"
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

const NewBacktestModal: React.FC<{
  onClose: () => void;
  onSubmit: (instruments: string[], timeframe: string) => void;
}> = ({ onClose, onSubmit }) => {
  const [selectedInstruments, setSelectedInstruments] = useState<string[]>([]);
  const [timeframe, setTimeframe] = useState<string>("H1");
  const [availableInstruments, setAvailableInstruments] = useState<string[]>(
    []
  );
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    const fetchInstruments = async () => {
      try {
        setLoading(true);
        const instruments = await oandaApiService.getInstruments();
        setAvailableInstruments(instruments);
      } catch (error) {
        console.error("Error fetching instruments:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchInstruments();
  }, []);

  const toggleInstrument = (instrument: string) => {
    if (selectedInstruments.includes(instrument)) {
      setSelectedInstruments(
        selectedInstruments.filter((i) => i !== instrument)
      );
    } else {
      setSelectedInstruments([...selectedInstruments, instrument]);
    }
  };

  const handleSubmit = () => {
    if (selectedInstruments.length === 0) {
      alert("Please select at least one instrument");
      return;
    }

    onSubmit(selectedInstruments, timeframe);
  };

  return (
    <div className="fixed inset-0 bg-gray-600 bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-lg w-full max-w-3xl overflow-hidden">
        <div className="flex justify-between items-center p-4 border-b">
          <h2 className="text-xl font-semibold">Run New Backtest</h2>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700"
          >
            <svg
              className="w-6 h-6"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              xmlns="http://www.w3.org/2000/svg"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        <div className="p-6">
          <div className="mb-6">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Timeframe
            </label>
            <select
              value={timeframe}
              onChange={(e) => setTimeframe(e.target.value)}
              className="w-full p-2 border rounded-md"
            >
              <option value="M1">1 Minute</option>
              <option value="M5">5 Minutes</option>
              <option value="M15">15 Minutes</option>
              <option value="M30">30 Minutes</option>
              <option value="H1">1 Hour</option>
              <option value="H4">4 Hours</option>
              <option value="D">1 Day</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Select Instruments
              {loading && (
                <span className="ml-2 text-gray-500 text-xs">(Loading...)</span>
              )}
            </label>

            {loading ? (
              <div className="flex justify-center p-4">
                <svg
                  className="animate-spin h-6 w-6 text-blue-600"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  ></circle>
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  ></path>
                </svg>
              </div>
            ) : (
              <div className="grid grid-cols-3 gap-2 max-h-60 overflow-y-auto p-2 border rounded-md">
                {availableInstruments.map((instrument) => (
                  <div key={instrument} className="flex items-center">
                    <input
                      type="checkbox"
                      id={`instrument-${instrument}`}
                      checked={selectedInstruments.includes(instrument)}
                      onChange={() => toggleInstrument(instrument)}
                      className="mr-2"
                    />
                    <label
                      htmlFor={`instrument-${instrument}`}
                      className="text-sm"
                    >
                      {instrument}
                    </label>
                  </div>
                ))}
              </div>
            )}

            <div className="mt-2 text-sm text-gray-500">
              Selected: {selectedInstruments.length} instruments
            </div>
          </div>
        </div>

        <div className="bg-gray-50 p-4 border-t flex justify-end">
          <button onClick={onClose} className="btn-secondary mr-2">
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            className="btn-primary"
            disabled={loading || selectedInstruments.length === 0}
          >
            Run Backtest
          </button>
        </div>
      </div>
    </div>
  );
};

const Backtests: React.FC = () => {
  const [backtests, setBacktests] = useState<BacktestResult[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [selectedBacktestId, setSelectedBacktestId] = useState<string | null>(
    null
  );
  const [sortField, setSortField] =
    useState<keyof BacktestResult>("performance");
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("desc");
  const [showNewBacktestModal, setShowNewBacktestModal] =
    useState<boolean>(false);
  const [runningBacktest, setRunningBacktest] = useState<boolean>(false);

  useEffect(() => {
    const fetchBacktests = async () => {
      try {
        setLoading(true);
        const data = await oandaApiService.getBacktests();
        setBacktests(data);
      } catch (error) {
        console.error("Error fetching backtests:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchBacktests();
  }, []);

  const handleSort = (field: keyof BacktestResult) => {
    if (field === sortField) {
      setSortDirection(sortDirection === "asc" ? "desc" : "asc");
    } else {
      setSortField(field);
      setSortDirection("desc");
    }
  };

  const sortedBacktests = [...backtests].sort((a, b) => {
    const directionMultiplier = sortDirection === "asc" ? 1 : -1;
    const aValue = a[sortField];
    const bValue = b[sortField];

    if (typeof aValue === "string" && typeof bValue === "string") {
      return directionMultiplier * aValue.localeCompare(bValue);
    }

    if (typeof aValue === "number" && typeof bValue === "number") {
      return directionMultiplier * (aValue - bValue);
    }

    return 0;
  });

  const renderSortIcon = (field: keyof BacktestResult) => {
    if (field !== sortField) {
      return null;
    }

    return <span className="ml-1">{sortDirection === "asc" ? "↑" : "↓"}</span>;
  };

  const handleRunBacktest = async (
    instruments: string[],
    timeframe: string
  ) => {
    try {
      setRunningBacktest(true);
      setShowNewBacktestModal(false);

      const backtestId = await oandaApiService.runBacktest(
        instruments,
        timeframe
      );

      // In a real implementation, you would poll for status until complete
      // For now, we'll simulate a delay and refresh the list
      setTimeout(async () => {
        const data = await oandaApiService.getBacktests();
        setBacktests(data);
        setRunningBacktest(false);
        alert(`Backtest ${backtestId} completed successfully!`);
      }, 3000);
    } catch (error) {
      console.error("Error running backtest:", error);
      setRunningBacktest(false);
      alert("Failed to run backtest. See console for details.");
    }
  };

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-gray-800">Backtest Results</h1>
        <div className="flex items-center">
          {runningBacktest && (
            <div className="flex items-center mr-4 text-blue-600">
              <svg
                className="animate-spin h-5 w-5 mr-2"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
              >
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                ></circle>
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                ></path>
              </svg>
              Running backtest...
            </div>
          )}
          <button
            className="btn-primary"
            onClick={() => setShowNewBacktestModal(true)}
            disabled={runningBacktest}
          >
            Run New Backtest
          </button>
        </div>
      </div>

      <div className="card">
        <div className="table-container">
          {loading ? (
            <div className="flex justify-center items-center p-8">
              <svg
                className="animate-spin h-8 w-8 text-blue-600 mr-3"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
              >
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                ></circle>
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                ></path>
              </svg>
              <span className="text-lg">Loading backtests...</span>
            </div>
          ) : backtests.length === 0 ? (
            <div className="flex flex-col items-center justify-center p-8">
              <p className="text-gray-500 mb-4">No backtests found</p>
              <button
                className="btn-primary"
                onClick={() => setShowNewBacktestModal(true)}
              >
                Run Your First Backtest
              </button>
            </div>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th
                    className="cursor-pointer hover:bg-gray-50"
                    onClick={() => handleSort("id")}
                  >
                    ID {renderSortIcon("id")}
                  </th>
                  <th
                    className="cursor-pointer hover:bg-gray-50"
                    onClick={() => handleSort("timeframe")}
                  >
                    Timeframe {renderSortIcon("timeframe")}
                  </th>
                  <th
                    className="cursor-pointer hover:bg-gray-50"
                    onClick={() => handleSort("performance")}
                  >
                    Performance {renderSortIcon("performance")}
                  </th>
                  <th
                    className="cursor-pointer hover:bg-gray-50"
                    onClick={() => handleSort("sharpeRatio")}
                  >
                    Sharpe {renderSortIcon("sharpeRatio")}
                  </th>
                  <th
                    className="cursor-pointer hover:bg-gray-50"
                    onClick={() => handleSort("maxDrawdown")}
                  >
                    Max DD {renderSortIcon("maxDrawdown")}
                  </th>
                  <th
                    className="cursor-pointer hover:bg-gray-50"
                    onClick={() => handleSort("winRate")}
                  >
                    Win Rate {renderSortIcon("winRate")}
                  </th>
                  <th
                    className="cursor-pointer hover:bg-gray-50"
                    onClick={() => handleSort("trades")}
                  >
                    Trades {renderSortIcon("trades")}
                  </th>
                  <th>Instruments</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {sortedBacktests.map((backtest) => (
                  <tr key={backtest.id}>
                    <td>{backtest.id}</td>
                    <td>{backtest.timeframe}</td>
                    <td className={backtest.performance >= 0 ? "gain" : "loss"}>
                      {backtest.performance >= 0 ? "+" : ""}
                      {backtest.performance.toFixed(2)}%
                    </td>
                    <td>{backtest.sharpeRatio.toFixed(2)}</td>
                    <td className="loss">
                      -{backtest.maxDrawdown.toFixed(2)}%
                    </td>
                    <td>{backtest.winRate.toFixed(2)}%</td>
                    <td>{backtest.trades}</td>
                    <td>
                      <div className="flex flex-wrap gap-1">
                        {backtest.instruments.slice(0, 3).map((instrument) => (
                          <span
                            key={instrument}
                            className="px-2 py-0.5 bg-blue-100 text-blue-800 rounded-full text-xs"
                          >
                            {instrument}
                          </span>
                        ))}
                        {backtest.instruments.length > 3 && (
                          <span className="px-2 py-0.5 bg-gray-100 text-gray-800 rounded-full text-xs">
                            +{backtest.instruments.length - 3} more
                          </span>
                        )}
                      </div>
                    </td>
                    <td>
                      <button
                        className="text-blue-600 hover:text-blue-800 mr-2"
                        onClick={() => setSelectedBacktestId(backtest.id)}
                      >
                        Details
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {selectedBacktestId && (
        <BacktestDetail
          backtestId={selectedBacktestId}
          onClose={() => setSelectedBacktestId(null)}
        />
      )}

      {showNewBacktestModal && (
        <NewBacktestModal
          onClose={() => setShowNewBacktestModal(false)}
          onSubmit={handleRunBacktest}
        />
      )}
    </div>
  );
};

export default Backtests;
