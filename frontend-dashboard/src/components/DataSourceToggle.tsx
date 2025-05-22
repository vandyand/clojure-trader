import React from "react";
import { useDataSource, DataSource } from "../lib/DataSourceContext";

interface DataSourceToggleProps {
  className?: string;
}

export const DataSourceToggle: React.FC<DataSourceToggleProps> = ({
  className = "",
}) => {
  const { dataSource, setDataSource } = useDataSource();

  const handleToggle = () => {
    setDataSource(dataSource === "DEMO" ? "LIVE" : "DEMO");
  };

  return (
    <div className={`data-source-toggle ${className}`}>
      <span>Data Source:</span>
      <button
        onClick={handleToggle}
        className={`toggle-button ${dataSource.toLowerCase()}`}
        aria-label={`Switch to ${dataSource === "DEMO" ? "LIVE" : "DEMO"} data`}
      >
        {dataSource}
      </button>
    </div>
  );
};
