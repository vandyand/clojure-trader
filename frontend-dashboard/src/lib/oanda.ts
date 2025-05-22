import axios from "axios";
import { DataSource } from "./DataSourceContext";

interface OandaConfig {
  dataSource: DataSource;
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

export interface CandlestickResponse {
  instrument: string;
  granularity: string;
  candles: Array<{
    time: string;
    bid?: {
      o: string;
      h: string;
      l: string;
      c: string;
    };
    ask?: {
      o: string;
      h: string;
      l: string;
      c: string;
    };
    mid?: {
      o: string;
      h: string;
      l: string;
      c: string;
    };
    complete: boolean;
    volume?: number;
  }>;
}

export interface TransactionsResponse {
  transactions: any[];
  [key: string]: any;
}

// Get configuration based on data source
export function getConfig(dataSource: DataSource): OandaConfig {
  return {
    dataSource,
  };
}

// Create Axios client with the given config
export function createOandaClient(config: OandaConfig) {
  return axios.create({
    baseURL: "/api/oanda/",
    headers: {
      "Content-Type": "application/json",
    },
    params: {
      dataSource: config.dataSource,
    },
  });
}

export async function getAccountSummary(
  dataSource: DataSource
): Promise<AccountSummary> {
  try {
    const config = getConfig(dataSource);
    const oandaClient = createOandaClient(config);

    const response = await oandaClient.get(`accounts/{accountId}/summary`);
    return response.data;
  } catch (error) {
    console.error("Error fetching account summary:", error);
    throw error;
  }
}

// Get the current price for an instrument
export async function getInstrumentPrice(
  dataSource: DataSource,
  instrument: string
): Promise<string | null> {
  try {
    const config = getConfig(dataSource);
    const oandaClient = createOandaClient(config);

    // Fetch the most recent candle for the instrument
    const response = await oandaClient.get(
      `instruments/${instrument}/candles`,
      {
        params: {
          count: 1, // Get only the most recent candle
          granularity: "S5", // 5-second granularity for most recent data
          price: "M", // Get midpoint price (can also use "A" for ask or "B" for bid)
        },
      }
    );

    const data: CandlestickResponse = response.data;

    if (data.candles && data.candles.length > 0) {
      const candle = data.candles[0];
      // Use the closing price from the most recent candle
      if (candle.mid) {
        return candle.mid.c;
      } else if (candle.ask) {
        return candle.ask.c;
      } else if (candle.bid) {
        return candle.bid.c;
      }
    }

    return null;
  } catch (error) {
    console.error(`Error fetching price for ${instrument}:`, error);
    return null;
  }
}

export async function getOpenPositions(
  dataSource: DataSource
): Promise<PositionsResponse> {
  try {
    const config = getConfig(dataSource);
    const oandaClient = createOandaClient(config);

    const response = await oandaClient.get(
      `accounts/{accountId}/openPositions`
    );

    let positions = response.data;

    // Enhance positions with current prices
    if (positions.positions && positions.positions.length > 0) {
      // Create an array of promises to fetch prices for all instruments in parallel
      const pricePromises = positions.positions.map(async (position: any) => {
        const currentPrice = await getInstrumentPrice(
          dataSource,
          position.instrument
        );
        return {
          ...position,
          currentPrice: currentPrice || "N/A",
        };
      });

      // Wait for all price fetch promises to resolve
      positions.positions = await Promise.all(pricePromises);
    }

    return positions;
  } catch (error) {
    console.error("Error fetching open positions:", error);
    throw error;
  }
}

export async function getAccountHistory(
  dataSource: DataSource,
  days = 30
): Promise<TransactionsResponse> {
  try {
    const config = getConfig(dataSource);
    const oandaClient = createOandaClient(config);

    const from = new Date();
    from.setDate(from.getDate() - days);

    const params = {
      from: from.toISOString(),
      to: new Date().toISOString(),
    };

    const response = await oandaClient.get(
      `accounts/{accountId}/transactions`,
      { params }
    );
    return response.data;
  } catch (error) {
    console.error("Error fetching account history:", error);
    throw error;
  }
}
