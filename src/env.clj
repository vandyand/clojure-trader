(ns env
  (:require
   [clojure.data.json :as json]
   [env :as env]))

(defn get-sensative-data [keywd]
  ((json/read-str (slurp ".sensative.json") :key-fn keyword) keywd))

(defn get-env-data [keywd]
  ((json/read-str (slurp ".env.json") :key-fn keyword) keywd))

(defn get-account-id [] 
  (let [account-type (get-env-data :OANDA_LIVE_OR_DEMO)]
   (if (= account-type "LIVE")
     (get-env-data :OANDA_LIVE_ACCOUNT_ID)
     (get-env-data :OANDA_DEMO_ACCOUNT_ID)
     )))
