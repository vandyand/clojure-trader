(ns env
  (:require
   [clojure.data.json :as json]
   [env :as env]))

(defn get-env-data [keywd]
  ((json/read-str (slurp ".env.json") :key-fn keyword) keywd))

(defn get-account-type []
  (get-env-data :OANDA_LIVE_OR_DEMO))

(defn is-live-account? []
  (= (get-account-type) "LIVE"))

(defn get-account-url []
  (if (is-live-account?)
    (get-env-data :OANDA_LIVE_URL)
    (get-env-data :OANDA_DEMO_URL)
    ))

(defn get-account-id [] 
   (if (is-live-account?)
     (get-env-data :OANDA_LIVE_ACCOUNT_ID)
     (get-env-data :OANDA_DEMO_ACCOUNT_ID)
     ))

;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;; sensitive
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
(defn get-sensitive-data [keywd]
  ((json/read-str (slurp ".sensitive.json") :key-fn keyword) keywd))

(defn get-oanda-api-key []
  (if (is-live-account?) 
    (get-sensitive-data :OANDA_LIVE_KEY)
    (get-sensitive-data :OANDA_DEMO_KEY)
    ))