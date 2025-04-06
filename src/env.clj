(ns env
  (:require
   [clojure.data.json :as json]
   [env :as env]))

(defn get-env-data [keywd]
  ((json/read-str (slurp ".env.json") :key-fn keyword) keywd))

(defn get-live-or-demo []
  (get-env-data :OANDA_LIVE_OR_DEMO))

(defn is-live-account? []
  (= (get-live-or-demo) "LIVE"))

(defn get-account-id []
  (if (is-live-account?)
    (get-env-data :OANDA_LIVE_ACCOUNT_ID)
    (get-env-data :OANDA_DEMO_ACCOUNT_ID)))

(defn get-sensitive-data [keywd]
  (or (System/getenv (name keywd))
      (try
        ((json/read-str (slurp ".sensitive.json") :key-fn keyword) keywd)
        (catch Exception e
          (println "Error fetching API data from .sensitive.json:" (.getMessage e))
          nil))))

(defn get-oanda-api-key []
  (if (is-live-account?)
    (get-sensitive-data :OANDA_LIVE_KEY)
    (get-sensitive-data :OANDA_DEMO_KEY)))
