(ns migrations.core
  (:require
   [clojure.java.jdbc :as jdbc]
   [clojure.string :as str]
   [db.core :as db]))

(def migrations
  "List of migrations in order of execution"
  [{:id "001-initial-schema"
    :description "Initial database schema"
    :up (fn [conn]
          ;; Create migrations table if it doesn't exist
          (jdbc/execute! conn
                         ["CREATE TABLE IF NOT EXISTS migrations (
                             id VARCHAR(255) PRIMARY KEY,
                             applied_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                             description TEXT
                          )"])

          ;; Create users table
          (jdbc/execute! conn
                         ["CREATE TABLE IF NOT EXISTS users (
                             id SERIAL PRIMARY KEY,
                             username VARCHAR(255) NOT NULL UNIQUE,
                             password VARCHAR(255) NOT NULL,
                             email VARCHAR(255) NOT NULL UNIQUE,
                             created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                           )"])

          ;; Create roles table
          (jdbc/execute! conn
                         ["CREATE TABLE IF NOT EXISTS roles (
                             id SERIAL PRIMARY KEY,
                             name VARCHAR(255) NOT NULL UNIQUE
                           )"])

          ;; Create user_roles table
          (jdbc/execute! conn
                         ["CREATE TABLE IF NOT EXISTS user_roles (
                             user_id INTEGER REFERENCES users(id),
                             role_id INTEGER REFERENCES roles(id),
                             PRIMARY KEY (user_id, role_id)
                           )"])

          ;; Create account_performance table
          (jdbc/execute! conn
                         ["CREATE TABLE IF NOT EXISTS account_performance (
                             id SERIAL PRIMARY KEY,
                             account_id VARCHAR(255) NOT NULL,
                             timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
                             balance DECIMAL(16,6) NOT NULL,
                             nav DECIMAL(16,6) NOT NULL,
                             currency VARCHAR(3) NOT NULL,
                             created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                           )"])

          ;; Create position_snapshots table
          (jdbc/execute! conn
                         ["CREATE TABLE IF NOT EXISTS position_snapshots (
                             id SERIAL PRIMARY KEY,
                             account_id VARCHAR(255) NOT NULL,
                             instrument VARCHAR(255) NOT NULL,
                             timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
                             units INTEGER NOT NULL,
                             avg_price DECIMAL(16,6) NOT NULL,
                             current_price DECIMAL(16,6) NOT NULL,
                             pnl DECIMAL(16,6) NOT NULL,
                             pnl_percent DECIMAL(16,6) NOT NULL,
                             created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                           )"])

          ;; Insert default roles
          (jdbc/execute! conn
                         ["INSERT INTO roles (name) VALUES ('admin') ON CONFLICT (name) DO NOTHING"])
          (jdbc/execute! conn
                         ["INSERT INTO roles (name) VALUES ('user') ON CONFLICT (name) DO NOTHING"]))}

   ;; Add performance indexes and monitoring table
   {:id "002-performance-indexes"
    :description "Add indexes for performance tables and monitoring"
    :up (fn [conn]
          ;; Add indexes to account_performance
          (jdbc/execute! conn
                         ["CREATE INDEX IF NOT EXISTS idx_account_performance_account_id 
                            ON account_performance(account_id)"])
          (jdbc/execute! conn
                         ["CREATE INDEX IF NOT EXISTS idx_account_performance_timestamp 
                            ON account_performance(timestamp)"])
          (jdbc/execute! conn
                         ["CREATE INDEX IF NOT EXISTS idx_account_performance_account_timestamp 
                            ON account_performance(account_id, timestamp)"])

          ;; Add indexes to position_snapshots
          (jdbc/execute! conn
                         ["CREATE INDEX IF NOT EXISTS idx_position_snapshots_account_id 
                            ON position_snapshots(account_id)"])
          (jdbc/execute! conn
                         ["CREATE INDEX IF NOT EXISTS idx_position_snapshots_instrument 
                            ON position_snapshots(instrument)"])
          (jdbc/execute! conn
                         ["CREATE INDEX IF NOT EXISTS idx_position_snapshots_timestamp 
                            ON position_snapshots(timestamp)"])
          (jdbc/execute! conn
                         ["CREATE INDEX IF NOT EXISTS idx_position_snapshots_account_instrument 
                            ON position_snapshots(account_id, instrument)"])

          ;; Create system_monitoring table
          (jdbc/execute! conn
                         ["CREATE TABLE IF NOT EXISTS system_monitoring (
                             id SERIAL PRIMARY KEY,
                             event_type VARCHAR(255) NOT NULL,
                             event_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                             description TEXT,
                             status VARCHAR(50) NOT NULL,
                             details JSONB
                           )"])

          ;; Create API request log table
          (jdbc/execute! conn
                         ["CREATE TABLE IF NOT EXISTS api_request_log (
                             id SERIAL PRIMARY KEY,
                             request_path VARCHAR(255) NOT NULL,
                             request_method VARCHAR(10) NOT NULL,
                             user_id INTEGER,
                             ip_address VARCHAR(50),
                             request_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                             response_status INTEGER,
                             response_time_ms INTEGER,
                             user_agent TEXT
                           )"])
          (jdbc/execute! conn
                         ["CREATE INDEX IF NOT EXISTS idx_api_request_log_path
                            ON api_request_log(request_path)"])
          (jdbc/execute! conn
                         ["CREATE INDEX IF NOT EXISTS idx_api_request_log_timestamp
                            ON api_request_log(request_timestamp)"]))}

   ;; Add more migrations here as needed
   ])

(defn get-applied-migrations
  "Get all migrations that have already been applied"
  [conn]
  (try
    (jdbc/query conn ["SELECT id FROM migrations ORDER BY applied_at"])
    (catch Exception _
      [])))

(defn mark-migration-applied
  "Mark a migration as applied"
  [conn migration]
  (jdbc/insert! conn :migrations
                {:id (:id migration)
                 :description (:description migration)}))

(defn run-migrations
  "Run all pending migrations"
  []
  (println "Running database migrations...")
  (try
    (jdbc/with-db-transaction [tx db/db-spec]
      (try
        ;; Create migrations table if it doesn't exist
        (jdbc/execute! tx
                       ["CREATE TABLE IF NOT EXISTS migrations (
                           id VARCHAR(255) PRIMARY KEY,
                           applied_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                           description TEXT
                        )"])
        (catch Exception e
          (println "Error creating migrations table:" (.getMessage e)))))

    (let [applied-migrations (set (map :id (get-applied-migrations db/db-spec)))]
      (doseq [migration migrations]
        (let [id (:id migration)]
          (if (contains? applied-migrations id)
            (println (str "Skipping migration " id " (already applied)"))
            (try
              (println (str "Applying migration " id ": " (:description migration)))
              (jdbc/with-db-transaction [tx db/db-spec]
                ((:up migration) tx)
                (mark-migration-applied tx migration))
              (println (str "Migration " id " applied successfully"))
              (catch Exception e
                (println (str "Error applying migration " id ": " (.getMessage e)))
                (.printStackTrace e)))))))
    (println "Database migrations complete")
    (catch Exception e
      (println "Error running migrations:" (.getMessage e))
      (.printStackTrace e))))

;; Run migrations when namespace is loaded
(defn init []
  (run-migrations)) 