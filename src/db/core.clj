(ns db.core
  (:require
   [clojure.java.jdbc :as jdbc]
   [environ.core :refer [env]]
   [clojure.string :as str]))

;; Database connection configuration
(def db-spec
  (if-let [database-url (System/getenv "DATABASE_URL")]
    ;; Production database URL from Heroku
    {:connection-uri database-url}
    ;; Local development database
    {:dbtype "postgresql"
     :dbname "clojure_trader"
     :host "localhost"
     :user "postgres"
     :password "postgres"
     :ssl false}))

;; Register PostgreSQL driver explicitly
(try
  (Class/forName "org.postgresql.Driver")
  (println "PostgreSQL driver loaded successfully")
  (catch Exception e
    (println "Failed to load PostgreSQL driver:" (.getMessage e))))

;; Initialize the database by creating tables if they don't exist
(defn init-db! []
  (try
    (println "Initializing database...")
    (println "Using database connection:" db-spec)

    ;; Create account_performance table
    (jdbc/execute! db-spec
                   ["CREATE TABLE IF NOT EXISTS account_performance (
          id SERIAL PRIMARY KEY,
          account_id VARCHAR(255) NOT NULL,
          timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
          balance DECIMAL(20, 5) NOT NULL,
          nav DECIMAL(20, 5) NOT NULL,
          currency VARCHAR(10) NOT NULL
        )"])

    ;; Create position_snapshots table
    (jdbc/execute! db-spec
                   ["CREATE TABLE IF NOT EXISTS position_snapshots (
          id SERIAL PRIMARY KEY,
          account_id VARCHAR(255) NOT NULL,
          instrument VARCHAR(255) NOT NULL,
          timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
          units INTEGER NOT NULL,
          avg_price DECIMAL(20, 5) NOT NULL,
          current_price DECIMAL(20, 5) NOT NULL,
          pnl DECIMAL(20, 5) NOT NULL,
          pnl_percent DECIMAL(10, 5) NOT NULL
        )"])

    ;; Convert tables to TimescaleDB hypertables if extension is available
    (try
      ;; First, enable the TimescaleDB extension
      (jdbc/execute! db-spec ["CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE"])

      ;; Convert tables to hypertables
      (jdbc/execute! db-spec
                     ["SELECT create_hypertable('account_performance', 'timestamp', if_not_exists => TRUE)"])
      (jdbc/execute! db-spec
                     ["SELECT create_hypertable('position_snapshots', 'timestamp', if_not_exists => TRUE)"])

      (println "TimescaleDB hypertables created successfully")
      (catch Exception e
        (println "Warning: Could not create TimescaleDB hypertables. This is expected in development: " (.getMessage e))))

    (println "Database initialization completed successfully.")
    (catch Exception e
      (println "Error initializing database:" (.getMessage e))
      (.printStackTrace e))))

;; Format account data for storage
(defn format-account-data [account]
  {:account_id (:id account)
   :timestamp (java.sql.Timestamp. (long (:timestamp account)))
   :balance (bigdec (:balance account))
   :nav (bigdec (:nav account))
   :currency (:currency account)})

;; Save account performance data
(defn save-account-performance [account]
  (try
    (when (and account (:nav account))
      (jdbc/insert! db-spec :account_performance (format-account-data account)))
    (catch Exception e
      (println "Error saving account performance:" (.getMessage e)))))

;; Format position data for storage
(defn format-position-data [position account-id]
  {:account_id account-id
   :instrument (:instrument position)
   :timestamp (java.sql.Timestamp. (long (:timestamp position)))
   :units (int (:units position))
   :avg_price (bigdec (:avgPrice position))
   :current_price (bigdec (:currentPrice position))
   :pnl (bigdec (:pnl position))
   :pnl_percent (bigdec (:pnlPercent position))})

;; Save position snapshot data
(defn save-position-snapshot [position account-id]
  (try
    (jdbc/insert! db-spec :position_snapshots (format-position-data position account-id))
    (catch Exception e
      (println "Error saving position snapshot:" (.getMessage e)))))

;; Get account performance history for a specific account
(defn get-account-performance-history [account-id days]
  (try
    (let [query ["SELECT timestamp, balance, nav 
                  FROM account_performance 
                  WHERE account_id = ? 
                  AND timestamp > now() - interval '? days'
                  ORDER BY timestamp"
                 account-id days]
          results (jdbc/query db-spec query)]
      (map (fn [row]
             {:timestamp (.getTime (:timestamp row))
              :value (double (:nav row))
              :balance (double (:balance row))})
           results))
    (catch Exception e
      (println "Error getting account performance history:" (.getMessage e))
      [])))

;; Get performance history for all accounts
(defn get-all-accounts-performance-history [days]
  (try
    (let [query ["SELECT a.timestamp, a.account_id, a.nav, a.balance
                  FROM account_performance a
                  INNER JOIN (
                    SELECT account_id, MAX(timestamp) as max_time
                    FROM account_performance
                    WHERE timestamp > now() - interval '? days'
                    GROUP BY account_id, date_trunc('day', timestamp)
                  ) b ON a.account_id = b.account_id AND a.timestamp = b.max_time
                  ORDER BY a.timestamp"
                 days]
          results (jdbc/query db-spec query)]
      (map (fn [row]
             {:timestamp (.getTime (:timestamp row))
              :account_id (:account_id row)
              :value (double (:nav row))
              :balance (double (:balance row))})
           results))
    (catch Exception e
      (println "Error getting all accounts performance history:" (.getMessage e))
      [])))

;; Get time-bucketed performance data for charts
(defn get-performance-time-buckets [account-id interval days]
  (try
    (let [query ["SELECT 
                    time_bucket('? hours', timestamp) as bucket,
                    AVG(nav) as avg_nav,
                    MAX(nav) as max_nav,
                    MIN(nav) as min_nav,
                    FIRST(nav, timestamp) as first_nav,
                    LAST(nav, timestamp) as last_nav
                  FROM account_performance
                  WHERE account_id = ?
                  AND timestamp > now() - interval '? days'
                  GROUP BY bucket
                  ORDER BY bucket"
                 interval account-id days]
          results (jdbc/query db-spec query)]
      (map (fn [row]
             {:timestamp (.getTime (:bucket row))
              :value (double (:last_nav row))
              :high (double (:max_nav row))
              :low (double (:min_nav row))})
           results))
    (catch Exception e
      (println "Error getting performance time buckets:" (.getMessage e))
      [])))

;; Initialize the database when this namespace is loaded
(init-db!)