import React from 'react';
import AccountSummary from '../components/AccountSummary';
import PerformanceChart from '../components/PerformanceChart';
import PositionsTable from '../components/PositionsTable';
import { useTradingContext } from '../context/TradingContext';

const Dashboard: React.FC = () => {
  const { isLoading, error, refreshData } = useTradingContext();
  
  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-gray-800">Trading Dashboard</h1>
        <button 
          className="btn-primary flex items-center"
          onClick={refreshData}
          disabled={isLoading}
        >
          {isLoading ? (
            <>
              <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              Refreshing...
            </>
          ) : (
            'Refresh Data'
          )}
        </button>
      </div>
      
      {error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-md text-red-600">
          {error}
        </div>
      )}
      
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        <div className="lg:col-span-2">
          <PerformanceChart />
        </div>
        <div>
          <AccountSummary />
        </div>
      </div>
      
      <div className="mb-6">
        <PositionsTable />
      </div>
    </div>
  );
};

export default Dashboard; 