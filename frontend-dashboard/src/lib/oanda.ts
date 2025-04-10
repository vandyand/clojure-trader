import axios from "axios";

interface OandaConfig {
  baseURL: string;
  apiKey: string;
  accountId: string;
}

export interface AccountSummary {
  account: {
    id: string;
    balance: string;
    unrealizedPL: string;
    NAV: string;
    marginUsed: string;
    marginAvailable: string;
    marginCloseoutPercent: string;
    [key: string]: any;
  };
}

export interface PositionsResponse {
  positions: Array<{
    instrument: string;
    long: {
      units: string;
      averagePrice: string;
      unrealizedPL: string;
      [key: string]: any;
    };
    short: {
      units: string;
      averagePrice: string;
      unrealizedPL: string;
      [key: string]: any;
    };
    currentPrice?: string;
    [key: string]: any;
  }>;
}

export interface TransactionsResponse {
  transactions: any[];
  [key: string]: any;
}

const ENV =
  process.env.REACT_APP_OANDA_LIVE_OR_DEMO === "LIVE" ? "LIVE" : "DEMO";

const config: OandaConfig = {
  baseURL:
    ENV === "LIVE"
      ? process.env.REACT_APP_OANDA_LIVE_URL ||
        "https://api-fxtrade.oanda.com/v3/"
      : process.env.REACT_APP_OANDA_DEMO_URL ||
        "https://api-fxpractice.oanda.com/v3/",
  apiKey:
    ENV === "LIVE"
      ? process.env.REACT_APP_OANDA_LIVE_KEY || ""
      : process.env.REACT_APP_OANDA_DEMO_KEY || "",
  accountId:
    ENV === "LIVE"
      ? process.env.REACT_APP_OANDA_LIVE_ACCOUNT_ID || ""
      : process.env.REACT_APP_OANDA_DEMO_ACCOUNT_ID || "",
};

const oandaClient = axios.create({
  baseURL: config.baseURL,
  headers: {
    Authorization: `Bearer ${config.apiKey}`,
    "Content-Type": "application/json",
  },
});

export async function getAccountSummary(): Promise<AccountSummary> {
  try {
    const response = await oandaClient.get(
      `accounts/${config.accountId}/summary`
    );
    return response.data;
  } catch (error) {
    console.error("Error fetching account summary:", error);
    throw error;
  }
}

export async function getOpenPositions(): Promise<PositionsResponse> {
  try {
    const response = await oandaClient.get(
      `accounts/${config.accountId}/openPositions`
    );
    return response.data;
  } catch (error) {
    console.error("Error fetching open positions:", error);
    throw error;
  }
}

export async function getAccountHistory(
  days = 30
): Promise<TransactionsResponse> {
  try {
    const from = new Date();
    from.setDate(from.getDate() - days);

    const params = {
      from: from.toISOString(),
      to: new Date().toISOString(),
    };

    const response = await oandaClient.get(
      `accounts/${config.accountId}/transactions`,
      { params }
    );
    return response.data;
  } catch (error) {
    console.error("Error fetching account history:", error);
    throw error;
  }
}
