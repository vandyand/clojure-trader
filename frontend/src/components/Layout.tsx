import React, { ReactNode, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { useTradingContext } from "../context/TradingContext";

interface NavItem {
  path: string;
  label: string;
  icon: string;
}

interface LayoutProps {
  children: ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  const location = useLocation();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const { apiSource, setApiSource, isLoading } = useTradingContext();

  const navItems: NavItem[] = [
    {
      path: "/",
      label: "Dashboard",
      icon: "M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6",
    },
    {
      path: "/positions",
      label: "Positions",
      icon: "M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4",
    },
    {
      path: "/performance",
      label: "Performance",
      icon: "M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z",
    },
    // Backtests page hidden until fully implemented
    // {
    //   path: "/backtests",
    //   label: "Backtests",
    //   icon: "M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z",
    // },
  ];

  const toggleDataSource = () => {
    setApiSource(apiSource === "mock" ? "oanda" : "mock");
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex">
              <div className="flex-shrink-0 flex items-center">
                <span className="text-xl font-bold text-blue-600">
                  Clojure Trader
                </span>
              </div>
            </div>

            <div className="hidden md:ml-6 md:flex md:items-center md:space-x-4">
              {navItems.map((item) => (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`px-3 py-2 rounded-md text-sm font-medium ${
                    location.pathname === item.path
                      ? "bg-blue-100 text-blue-700"
                      : "text-gray-600 hover:bg-gray-100 hover:text-gray-900"
                  }`}
                >
                  {item.label}
                </Link>
              ))}

              {/* Data Source Toggle */}
              <div className="ml-4 flex items-center">
                <span className="mr-2 text-sm text-gray-600">Data Source:</span>
                <button
                  onClick={toggleDataSource}
                  disabled={isLoading}
                  className={`px-3 py-1 rounded-md text-sm font-medium transition-colors ${
                    isLoading ? "opacity-50 cursor-not-allowed" : ""
                  } ${
                    apiSource === "mock"
                      ? "bg-gray-200 text-gray-800"
                      : "bg-blue-600 text-white"
                  }`}
                >
                  {isLoading
                    ? "Loading..."
                    : apiSource === "mock"
                    ? "Mock"
                    : "OANDA"}
                </button>
              </div>
            </div>

            <div className="flex items-center md:hidden">
              <button
                type="button"
                className="inline-flex items-center justify-center p-2 rounded-md text-gray-500 hover:text-gray-900 hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-blue-500"
                onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
              >
                <span className="sr-only">Open main menu</span>
                <svg
                  className="h-6 w-6"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  {isMobileMenuOpen ? (
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M6 18L18 6M6 6l12 12"
                    />
                  ) : (
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M4 6h16M4 12h16M4 18h16"
                    />
                  )}
                </svg>
              </button>
            </div>
          </div>
        </div>

        {/* Mobile menu */}
        {isMobileMenuOpen && (
          <div className="md:hidden">
            <div className="pt-2 pb-3 space-y-1">
              {navItems.map((item) => (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`block px-3 py-2 rounded-md text-base font-medium ${
                    location.pathname === item.path
                      ? "bg-blue-100 text-blue-700"
                      : "text-gray-600 hover:bg-gray-100 hover:text-gray-900"
                  }`}
                  onClick={() => setIsMobileMenuOpen(false)}
                >
                  {item.label}
                </Link>
              ))}

              {/* Data Source Toggle for Mobile */}
              <div className="px-3 py-2 flex items-center justify-between">
                <span className="text-base text-gray-600">Data Source:</span>
                <button
                  onClick={toggleDataSource}
                  disabled={isLoading}
                  className={`px-3 py-1 rounded-md text-sm font-medium ${
                    isLoading ? "opacity-50 cursor-not-allowed" : ""
                  } ${
                    apiSource === "mock"
                      ? "bg-gray-200 text-gray-800"
                      : "bg-blue-600 text-white"
                  }`}
                >
                  {isLoading
                    ? "Loading..."
                    : apiSource === "mock"
                    ? "Mock"
                    : "OANDA"}
                </button>
              </div>
            </div>
          </div>
        )}
      </header>

      {/* Main content */}
      <main>
        <div className="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
          {children}
        </div>
      </main>

      {/* Footer */}
      <footer className="bg-white shadow-inner mt-8 py-4">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <p className="text-center text-sm text-gray-500">
            &copy; {new Date().getFullYear()} Clojure Trader. All rights
            reserved.
          </p>
        </div>
      </footer>
    </div>
  );
};

export default Layout;
