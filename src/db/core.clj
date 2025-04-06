(ns db.core
  (:require [next.jdbc :as jdbc]
            [next.jdbc.sql :as sql]
            [next.jdbc.result-set :as rs]
            [clojure.java.io :as io]))

;; Define the database path
(def db-path "data/performance_history.db")

;; Ensure data directory exists
(defn ensure-db-dir []
  (let [data-dir (io/file "data")]
    (when-not (.exists data-dir)
      (.mkdir data-dir))))

;; Initialize the database connection
(defn db-spec []
  (ensure-db-dir)
  {:dbtype "sqlite"
   :dbname db-path})

;; Create tables if they don't exist
(defn init-db []
  (with-open [conn (jdbc/get-connection (db-spec))]
    (jdbc/execute! conn ["
      CREATE TABLE IF NOT EXISTS account_performance (
        timestamp INTEGER NOT NULL,
        account_id TEXT NOT NULL,
        balance REAL NOT NULL,
        nav REAL NOT NULL,
        unrealized_pl REAL,
        currency TEXT,
        PRIMARY KEY (timestamp, account_id)
      )
    "])
    (jdbc/execute! conn ["
      CREATE TABLE IF NOT EXISTS position_snapshots (
        timestamp INTEGER NOT NULL,
        instrument TEXT NOT NULL,
        units INTEGER NOT NULL,
        avg_price REAL NOT NULL,
        current_price REAL NOT NULL,
        pnl REAL NOT NULL,
        pnl_percent REAL,
        account_id TEXT NOT NULL,
        PRIMARY KEY (timestamp, instrument, account_id)
      )
    "])
    (jdbc/execute! conn ["
      CREATE INDEX IF NOT EXISTS idx_account_performance_timestamp 
      ON account_performance (timestamp)
    "])
    (jdbc/execute! conn ["
      CREATE INDEX IF NOT EXISTS idx_account_performance_account_id 
      ON account_performance (account_id)
    "])
    (jdbc/execute! conn ["
      CREATE INDEX IF NOT EXISTS idx_position_snapshots_timestamp 
      ON position_snapshots (timestamp)
    "])
    (jdbc/execute! conn ["
      CREATE INDEX IF NOT EXISTS idx_position_snapshots_account_id 
      ON position_snapshots (account_id)
    "])))

;; Save account performance snapshot
(defn save-account-performance [account]
  (try
    (with-open [conn (jdbc/get-connection (db-spec))]
      (sql/insert! conn :account_performance
                   {:timestamp (System/currentTimeMillis)
                    :account_id (:id account)
                    :balance (:balance account)
                    :nav (:nav account)
                    :unrealized_pl (:unrealizedPL account)
                    :currency (:currency account)}
                   {:builder-fn rs/as-unqualified-maps}))
    (catch Exception e
      (println "Error saving account performance:" (.getMessage e))
      nil)))

;; Save position snapshot
(defn save-position-snapshot [position account-id]
  (try
    (with-open [conn (jdbc/get-connection (db-spec))]
      (sql/insert! conn :position_snapshots
                   {:timestamp (System/currentTimeMillis)
                    :instrument (:instrument position)
                    :units (:units position)
                    :avg_price (:avgPrice position)
                    :current_price (:currentPrice position)
                    :pnl (:pnl position)
                    :pnl_percent (:pnlPercent position)
                    :account_id account-id}
                   {:builder-fn rs/as-unqualified-maps}))
    (catch Exception e
      (println "Error saving position snapshot:" (.getMessage e))
      nil)))

;; Get account performance history
(defn get-account-performance-history
  ([account-id]
   (get-account-performance-history account-id 30)) ; Default to 30 days
  ([account-id days]
   (try
     (let [start-time (- (System/currentTimeMillis) (* days 24 60 60 1000))]
       (with-open [conn (jdbc/get-connection (db-spec))]
         (sql/query conn ["
           SELECT timestamp, balance, nav, unrealized_pl
           FROM account_performance
           WHERE account_id = ? AND timestamp >= ?
           ORDER BY timestamp ASC
         " account-id start-time]
                    {:builder-fn rs/as-unqualified-maps})))
     (catch Exception e
       (println "Error fetching account performance history:" (.getMessage e))
       []))))

;; Get all accounts performance history
(defn get-all-accounts-performance-history
  ([]
   (get-all-accounts-performance-history 30)) ; Default to 30 days
  ([days]
   (try
     (let [start-time (- (System/currentTimeMillis) (* days 24 60 60 1000))]
       (with-open [conn (jdbc/get-connection (db-spec))]
         (sql/query conn ["
           SELECT timestamp, account_id, balance, nav, unrealized_pl
           FROM account_performance
           WHERE timestamp >= ?
           ORDER BY timestamp ASC
         " start-time]
                    {:builder-fn rs/as-unqualified-maps})))
     (catch Exception e
       (println "Error fetching all accounts performance history:" (.getMessage e))
       []))))

;; Initialize the database when this namespace is loaded
(init-db)