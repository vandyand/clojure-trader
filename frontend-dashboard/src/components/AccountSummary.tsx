import React, { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import * as oandaApi from "../lib/oanda";
import * as dataService from "../lib/dataService";
import { useDataSource } from "../lib/DataSourceContext";

interface AccountSummaryProps {
  refreshInterval?: number;
}

interface AccountData {
  account: {
    id: string;
    balance: string;
    unrealizedPL: string;
    NAV: string;
    marginUsed: string;
    marginAvailable: string;
    marginCloseoutPercent: string;
  };
}

export const AccountSummary: React.FC<AccountSummaryProps> = ({
  refreshInterval = 60000, // 1 minute default refresh
}) => {
  const { dataSource } = useDataSource();

  const {
    data: accountSummary,
    isLoading,
    error,
  } = useQuery({
    queryKey: ["accountSummary", dataSource],
    queryFn: () => oandaApi.getAccountSummary(dataSource),
    refetchInterval: refreshInterval,
  });

  // Use useEffect to save data when accountSummary changes
  useEffect(() => {
    if (accountSummary) {
      dataService.saveAccountSnapshot(dataSource);
    }
  }, [accountSummary, dataSource]);

  if (isLoading) return <div>Loading account data...</div>;
  if (error) return <div>Error loading account data</div>;
  if (!accountSummary) return <div>No account data available</div>;

  const account = accountSummary.account;

  return (
    <div className="account-summary">
      <h2>Account Summary ({dataSource})</h2>
      <div className="summary-grid">
        <div className="summary-item">
          <h3>Account ID</h3>
          <p>{account.id}</p>
        </div>
        <div className="summary-item">
          <h3>Balance</h3>
          <p>${parseFloat(account.balance).toFixed(2)}</p>
        </div>
        <div className="summary-item">
          <h3>Unrealized P/L</h3>
          <p
            className={
              parseFloat(account.unrealizedPL) >= 0 ? "positive" : "negative"
            }
          >
            ${parseFloat(account.unrealizedPL).toFixed(2)}
          </p>
        </div>
        <div className="summary-item">
          <h3>NAV</h3>
          <p>${parseFloat(account.NAV).toFixed(2)}</p>
        </div>
        <div className="summary-item">
          <h3>Margin Used</h3>
          <p>${parseFloat(account.marginUsed).toFixed(2)}</p>
        </div>
        <div className="summary-item">
          <h3>Margin Available</h3>
          <p>${parseFloat(account.marginAvailable).toFixed(2)}</p>
        </div>
        <div className="summary-item">
          <h3>Margin Closeout Percent</h3>
          <p>{parseFloat(account.marginCloseoutPercent) * 100}%</p>
        </div>
      </div>
    </div>
  );
};
