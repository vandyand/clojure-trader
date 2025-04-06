import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  ReactNode,
} from "react";
import axios from "axios";

// Define the API URL based on environment
const API_URL =
  process.env.REACT_APP_CLOJURE_API_URL ||
  "https://clojure-trader-api-18279899daf7.herokuapp.com";

// Define user type
export interface User {
  username: string;
  email: string;
  roles: string[];
}

// Define auth state
interface AuthState {
  isAuthenticated: boolean;
  user: User | null;
  token: string | null;
  loading: boolean;
  error: string | null;
  login: (username: string, password: string) => Promise<boolean>;
  register: (
    username: string,
    password: string,
    email: string
  ) => Promise<boolean>;
  logout: () => void;
  clearError: () => void;
}

// Create context
const AuthContext = createContext<AuthState | undefined>(undefined);

// Provider props interface
interface AuthProviderProps {
  children: ReactNode;
}

// Create provider component
export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Initialize auth state from local storage
  useEffect(() => {
    const storedToken = localStorage.getItem("auth_token");
    const storedUser = localStorage.getItem("auth_user");

    if (storedToken && storedUser) {
      setToken(storedToken);
      setUser(JSON.parse(storedUser));
      setIsAuthenticated(true);

      // Add token to axios default headers
      axios.defaults.headers.common["Authorization"] = `Bearer ${storedToken}`;
    }

    setLoading(false);
  }, []);

  // Login function
  const login = async (
    username: string,
    password: string
  ): Promise<boolean> => {
    try {
      setLoading(true);
      setError(null);

      const response = await axios.post(`${API_URL}/api/auth/login`, {
        username,
        password,
      });

      if (response.data.status === "success" && response.data.token) {
        const { token, user } = response.data;

        // Store in state
        setToken(token);
        setUser(user);
        setIsAuthenticated(true);

        // Store in local storage
        localStorage.setItem("auth_token", token);
        localStorage.setItem("auth_user", JSON.stringify(user));

        // Add token to axios default headers
        axios.defaults.headers.common["Authorization"] = `Bearer ${token}`;

        return true;
      } else {
        setError(response.data.message || "Login failed");
        return false;
      }
    } catch (err: any) {
      setError(err.response?.data?.message || "Login failed");
      return false;
    } finally {
      setLoading(false);
    }
  };

  // Register function
  const register = async (
    username: string,
    password: string,
    email: string
  ): Promise<boolean> => {
    try {
      setLoading(true);
      setError(null);

      const response = await axios.post(`${API_URL}/api/auth/register`, {
        username,
        password,
        email,
      });

      if (response.data.status === "success") {
        return true;
      } else {
        setError(response.data.message || "Registration failed");
        return false;
      }
    } catch (err: any) {
      setError(err.response?.data?.message || "Registration failed");
      return false;
    } finally {
      setLoading(false);
    }
  };

  // Logout function
  const logout = () => {
    // Clear state
    setToken(null);
    setUser(null);
    setIsAuthenticated(false);

    // Clear local storage
    localStorage.removeItem("auth_token");
    localStorage.removeItem("auth_user");

    // Remove token from axios headers
    delete axios.defaults.headers.common["Authorization"];
  };

  // Clear error
  const clearError = () => {
    setError(null);
  };

  // Return provider
  return (
    <AuthContext.Provider
      value={{
        isAuthenticated,
        user,
        token,
        loading,
        error,
        login,
        register,
        logout,
        clearError,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

// Custom hook to use the context
export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};

export default AuthContext;
