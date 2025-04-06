(ns db.core
  (:require
   [clojure.java.jdbc :as jdbc]
   [environ.core :refer [env]]
   [clojure.string :as str])
  (:import
   (java.net URI)
   (org.postgresql Driver)))

(println "Loading db.core namespace")
(println "Registering PostgreSQL driver")

;; Explicitly register PostgreSQL driver
(try
  (Class/forName "org.postgresql.Driver")
  (println "PostgreSQL driver registered successfully")
  (catch Exception e
    (println "Error registering PostgreSQL driver:" (.getMessage e))))

(defn parse-db-url [url]
  (println "Parsing DB URL:" url)
  (try
    (let [uri (URI. url)
          host (.getHost uri)
          port (if (= -1 (.getPort uri)) 5432 (.getPort uri))
          path (.getPath uri)
          db-name (subs path 1)
          userinfo (or (.getUserInfo uri) "")
          [username password] (if (str/includes? userinfo ":")
                                (str/split userinfo #":")
                                [userinfo ""])]
      (println "Parsed DB components - host:" host "port:" port "db:" db-name "user:" username)
      {:dbtype "postgresql"
       :dbname db-name
       :host host
       :port port
       :user username
       :password password
       :ssl true
       :sslfactory "org.postgresql.ssl.NonValidatingFactory"})
    (catch Exception e
      (println "Error parsing DB URL:" (.getMessage e))
      (throw e))))

;; Define database specification
(def db-spec
  (let [db-url (System/getenv "DATABASE_URL")]
    (if db-url
      (do
        (println "Using DATABASE_URL from environment")
        (parse-db-url db-url))
      (do
        (println "Using local development database")
        {:subprotocol "sqlite"
         :subname "data/performance_history.db"}))))

(defn init-db! []
  (println "Initializing database with spec:" (pr-str (dissoc db-spec :password)))
  (try
    ;; Create performance_history table if it doesn't exist
    (jdbc/execute! db-spec
                   ["CREATE TABLE IF NOT EXISTS performance_history (
                   id SERIAL PRIMARY KEY,
                   user_id TEXT NOT NULL,
                   date TEXT NOT NULL,
                   balance REAL NOT NULL,
                   equity REAL NOT NULL,
                   pnl REAL NOT NULL,
                   drawdown REAL NOT NULL
                  )"])
    (println "Performance history table initialized successfully")
    (catch Exception e
      (println "Error initializing performance history table:" (.getMessage e))
      (.printStackTrace e))))

;; Save performance history entry
(defn save-performance! [user-id date balance equity pnl drawdown]
  (try
    (jdbc/insert! db-spec :performance_history
                  {:user_id user-id
                   :date date
                   :balance balance
                   :equity equity
                   :pnl pnl
                   :drawdown drawdown})
    (catch Exception e
      (println "Error saving performance:" (.getMessage e))
      nil)))

;; Get all performance history for a user
(defn get-user-performance [user-id]
  (try
    (jdbc/query db-spec
                ["SELECT * FROM performance_history WHERE user_id = ? ORDER BY date" user-id])
    (catch Exception e
      (println "Error retrieving user performance:" (.getMessage e))
      [])))

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