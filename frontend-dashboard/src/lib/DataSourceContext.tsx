import React, { createContext, useContext, useState, ReactNode } from "react";

export type DataSource = "DEMO" | "LIVE";

interface DataSourceContextType {
  dataSource: DataSource;
  setDataSource: (source: DataSource) => void;
}

const DataSourceContext = createContext<DataSourceContextType | undefined>(
  undefined
);

export const DataSourceProvider: React.FC<{ children: ReactNode }> = ({
  children,
}) => {
  // Initialize with environment variable or default to LIVE
  const initialSource =
    process.env.REACT_APP_OANDA_LIVE_OR_DEMO === "DEMO" ? "DEMO" : "LIVE";
  const [dataSource, setDataSource] = useState<DataSource>(initialSource);

  return (
    <DataSourceContext.Provider value={{ dataSource, setDataSource }}>
      {children}
    </DataSourceContext.Provider>
  );
};

export const useDataSource = (): DataSourceContextType => {
  const context = useContext(DataSourceContext);
  if (context === undefined) {
    throw new Error("useDataSource must be used within a DataSourceProvider");
  }
  return context;
};
