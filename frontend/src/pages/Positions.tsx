import React from "react";
import PositionsTable from "../components/PositionsTable";
import PositionComparisonChart from "../components/PositionComparisonChart";
import { useTradingContext } from "../context/TradingContext";

const Positions: React.FC = () => {
  const {
    accounts,
    positions,
    selectedAccountId,
    setSelectedAccountId,
    isLoading,
    refreshData,
  } = useTradingContext();

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-gray-800">Positions</h1>
        <button
          className="btn-primary flex items-center"
          onClick={refreshData}
          disabled={isLoading}
        >
          {isLoading ? (
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
              Refreshing...
            </>
          ) : (
            "Refresh Data"
          )}
        </button>
      </div>

      <div className="card mb-6">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between">
          <h2 className="text-lg font-semibold text-gray-800 mb-4 md:mb-0">
            Account Selection
          </h2>

          <div className="flex flex-wrap gap-2">
            <button
              className={`px-3 py-2 text-sm rounded-md ${
                selectedAccountId === null
                  ? "bg-blue-600 text-white"
                  : "bg-gray-100 text-gray-700 hover:bg-gray-200"
              }`}
              onClick={() => setSelectedAccountId(null)}
            >
              All Accounts
            </button>

            {accounts.map((account) => (
              <button
                key={account.id}
                className={`px-3 py-2 text-sm rounded-md ${
                  selectedAccountId === account.id
                    ? "bg-blue-600 text-white"
                    : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                }`}
                onClick={() => setSelectedAccountId(account.id)}
              >
                {account.name}
              </button>
            ))}
          </div>
        </div>
      </div>

      <PositionsTable />

      {/* Position Performance Comparison Chart */}
      {positions.length > 0 && (
        <div className="mt-6">
          <PositionComparisonChart positions={positions} />
        </div>
      )}

      <div className="mt-6">
        <h2 className="text-lg font-semibold text-gray-800 mb-4">
          Position Management
        </h2>
        <div className="card">
          <p className="text-gray-600 mb-4">
            Positions are managed through the automated trading strategies
            configured in the Clojure backend. Manual position management is not
            currently supported through this UI.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="p-4 border border-gray-200 rounded-md">
              <h3 className="font-medium text-gray-800 mb-2">
                Automated Strategies
              </h3>
              <p className="text-sm text-gray-600">
                Trading strategies are executed automatically based on the
                genetic algorithm parameters configured in the Clojure backend.
                Position sizes are optimized based on backtest performance.
              </p>
            </div>
            <div className="p-4 border border-gray-200 rounded-md">
              <h3 className="font-medium text-gray-800 mb-2">
                Risk Management
              </h3>
              <p className="text-sm text-gray-600">
                Position sizes are automatically scaled based on account balance
                and instrument volatility. Risk is distributed across multiple
                instruments and strategies.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Positions;
