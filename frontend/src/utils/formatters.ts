import { format, parseISO } from "date-fns";

/**
 * Format a number as currency
 */
export const formatCurrency = (
  value: number,
  currency: string = "USD",
  locale: string = "en-US"
): string => {
  return new Intl.NumberFormat(locale, {
    style: "currency",
    currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
};

/**
 * Format a number as percentage
 */
export const formatPercentage = (
  value: number,
  minimumFractionDigits: number = 2,
  maximumFractionDigits: number = 2
): string => {
  return new Intl.NumberFormat("en-US", {
    style: "percent",
    minimumFractionDigits,
    maximumFractionDigits,
  }).format(value / 100);
};

/**
 * Format a number with commas
 */
export const formatNumber = (
  value: number,
  minimumFractionDigits: number = 0,
  maximumFractionDigits: number = 2
): string => {
  return new Intl.NumberFormat("en-US", {
    minimumFractionDigits,
    maximumFractionDigits,
  }).format(value);
};

/**
 * Format a timestamp or date string
 */
export const formatDate = (
  date: number | string | Date,
  formatString: string = "MMM dd, yyyy"
): string => {
  try {
    // Handle case when the date is already pre-formatted (chart labels)
    if (typeof date === "string" && date.includes(",")) {
      return date;
    }

    // Handle partial date strings like "Apr 05" that are missing the year
    if (typeof date === "string" && /^[A-Za-z]{3}\s\d{1,2}$/.test(date)) {
      const currentYear = new Date().getFullYear();
      date = `${date}, ${currentYear}`;
      return date; // Return the formatted string directly
    }

    // Convert to Date object
    let dateObj: Date;
    let timestamp: number | undefined;

    if (typeof date === "number") {
      // If it's a timestamp
      dateObj = new Date(date);
      timestamp = date;
    } else if (typeof date === "string") {
      // If it's a string, try different parsing approaches
      if (date.match(/^\d+$/)) {
        // It's a numeric string, treat as timestamp
        timestamp = parseInt(date, 10);
        dateObj = new Date(timestamp);
      } else {
        try {
          dateObj = parseISO(date);
        } catch (e) {
          dateObj = new Date(date);
        }
      }
    } else if (date instanceof Date) {
      dateObj = date;
    } else {
      // If none of the above, return as is
      return String(date);
    }

    // For debugging
    if (process.env.NODE_ENV === "development") {
      console.debug(
        `Formatting date: ${date}, type: ${typeof date}, converted: ${dateObj}`
      );
    }

    // Validate date is valid
    if (isNaN(dateObj.getTime())) {
      console.warn(`Invalid date: ${date}, type: ${typeof date}`);

      // Try one more approach if we have a timestamp
      if (timestamp) {
        const newDate = new Date();
        newDate.setTime(timestamp);
        if (!isNaN(newDate.getTime())) {
          return format(newDate, formatString);
        }
      }

      return String(date);
    }

    // Format using date-fns
    return format(dateObj, formatString);
  } catch (e) {
    console.error("Error formatting date:", e, "for input:", date);
    return String(date);
  }
};

/**
 * Format a price value based on instrument
 */
export const formatPrice = (price: number, instrument: string): string => {
  // Determine precision based on instrument
  let precision = 4; // Default for forex pairs

  if (instrument.includes("JPY")) {
    precision = 3;
  } else if (instrument.includes("BTC") || instrument.includes("ETH")) {
    precision = 2;
  } else if (instrument.includes("XRP") || instrument.includes("DOGE")) {
    precision = 6;
  }

  return price.toFixed(precision);
};

/**
 * Format PnL with color class
 */
export const formatPnL = (
  pnl: number
): { value: string; className: string } => {
  const formatted = formatCurrency(Math.abs(pnl));
  const className = pnl >= 0 ? "gain" : "loss";
  const prefix = pnl >= 0 ? "+" : "-";

  return {
    value: `${prefix}${formatted}`,
    className,
  };
};

/**
 * Format PnL percentage with color class
 */
export const formatPnLPercentage = (
  pnlPercent: number
): { value: string; className: string } => {
  const formatted = formatPercentage(Math.abs(pnlPercent));
  const className = pnlPercent >= 0 ? "gain" : "loss";
  const prefix = pnlPercent >= 0 ? "+" : "-";

  return {
    value: `${prefix}${formatted}`,
    className,
  };
};
