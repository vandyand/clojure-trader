(ns arena.oanda_api
  (:require [clj-http.client :as client]
            [clojure.data.json :as json]))

(defn get-sensative-data [keywd]
  ((json/read-str (slurp ".sensative.json") :key-fn keyword) keywd))

(defn get-env-data [keywd]
  ((json/read-str (slurp ".env.json") :key-fn keyword) keywd))

(defn send-api-request [url]
  (let [headers {:headers {:Authorization (str "Bearer " (get-sensative-data :OANDA_API_KEY))}}]
    (client/get url headers)))

(defn parse-response-body [response]
  (json/read-str (response :body) :key-fn keyword))

(defn get-url [endpoint]
  (str (get-env-data :OANDA_API_URL) endpoint))

(defn get-api-data [endpoint]
  (-> endpoint (get-url) (send-api-request) (parse-response-body)))


;; ACCOUNT DATA FUNCTIONS


(defn get-accounts [] (get-api-data "accounts"))

(defn get-account-summary
  ([] (get-account-summary (get-env-data :OANDA_DEFAULT_ACCOUNT_ID)))
  ([account-id]
   (get-api-data (str "accounts/" account-id "/summary"))))

(defn get-account-instruments
  ([] (get-account-instruments (get-env-data :OANDA_DEFAULT_ACCOUNT_ID)))
  ([account-id]
   (get-api-data (str "accounts/" account-id "/instruments"))))


;; INSTRUMENT FUNCTION


(def eurusd-candles (get-api-data (str "instruments/" "EUR_USD" "/candles?count=10&granularity=M5")))
