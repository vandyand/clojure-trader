(ns nean.db-test
  (:require [clojure.java.jdbc :as jdbc]
            [clojure.string :as str]))

(defn print-db-info []
  (println "=== Database Connection Info ===")
  (println "DATABASE_URL:" (System/getenv "DATABASE_URL"))
  (println "============================"))

(defn test-postgres-connection []
  (println "Testing PostgreSQL connection...")
  (let [db-url (System/getenv "DATABASE_URL")
        db-spec (if db-url
                  {:connection-uri db-url}
                  {:dbtype "postgresql"
                   :dbname "clojure_trader"
                   :host "localhost"
                   :user "postgres"
                   :password "postgres"
                   :ssl false})]
    (try
      (let [result (jdbc/query db-spec ["SELECT current_timestamp"])]
        (println "Connection successful!")
        (println "Current timestamp:" (:current_timestamp (first result))))
      (catch Exception e
        (println "Connection failed:" (.getMessage e))
        (.printStackTrace e)))))

;; Add this to be called from server.clj
(defn run-db-tests []
  (print-db-info)
  (test-postgres-connection)) 