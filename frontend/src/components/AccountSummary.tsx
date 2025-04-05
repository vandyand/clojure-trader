import React from "react";
import { useTradingContext } from "../context/TradingContext";
import { formatCurrency } from "../utils/formatters";

const AccountSummary: React.FC = () => {
  const { accounts, accountsWorth, isLoading } = useTradingContext();

  if (isLoading && (!accounts.length || !accountsWorth)) {
    return (
      <div className="card animate-pulse">
        <div className="h-8 bg-gray-200 rounded w-1/3 mb-4"></div>
        <div className="h-16 bg-gray-200 rounded w-full mb-2"></div>
        <div className="h-8 bg-gray-200 rounded w-2/3"></div>
      </div>
    );
  }

  return (
    <div className="card">
      <h2 className="text-lg font-semibold text-gray-800 mb-4">
        Account Summary
      </h2>

      {accountsWorth && (
        <div className="mb-6">
          <div className="flex justify-between items-center mb-2">
            <span className="text-gray-600">Total Portfolio Value</span>
            <span className="text-xl font-bold">
              {formatCurrency(accountsWorth.total)}
            </span>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="p-3 bg-blue-50 rounded-md">
              <div className="text-sm text-gray-500">Oanda</div>
              <div className="font-medium">
                {formatCurrency(accountsWorth.oanda)}
              </div>
            </div>
            <div className="p-3 bg-purple-50 rounded-md">
              <div className="text-sm text-gray-500">Binance</div>
              <div className="font-medium">
                {formatCurrency(accountsWorth.binance)}
              </div>
            </div>
          </div>
        </div>
      )}

      <div>
        <h3 className="text-md font-medium text-gray-700 mb-2">
          Individual Accounts
        </h3>
        <div className="space-y-3">
          {accounts.map((account) => (
            <div
              key={account.id}
              className="flex justify-between items-center p-3 border border-gray-200 rounded-md"
            >
              <div>
                <div className="font-medium">{account.name}</div>
                <div className="text-sm text-gray-500">{account.id}</div>
              </div>
              <div className="text-right">
                <div className="font-medium">{formatCurrency(account.nav)}</div>
                <div className="text-sm text-gray-500">NAV</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default AccountSummary;
