(ns arena.oanda_api
  (:require [clj-http.client :as client]
            [clojure.pprint :as pp]
            [clojure.data.json :as json]))

(defn get-sensative-data [keywd]
  ((json/read-str (slurp ".sensative.json") :key-fn keyword) keywd))

(defn get-env-data [keywd]
  ((json/read-str (slurp ".env.json") :key-fn keyword) keywd))

(defn get-account-endpoint
  ([end] (get-account-endpoint (get-env-data :OANDA_DEFAULT_ACCOUNT_ID) end))
  ([account-id end]
   (str "accounts/" account-id "/" end)))

(defn get-headers [] {:Authorization (str "Bearer " (get-sensative-data :OANDA_API_KEY)) :Accept-Datetime-Format "UNIX"})

;; SEND REQUESTS

(defn send-api-get-request
  ([url]
   (let [options {:headers (get-headers)}]
     (client/get url options))))

(defn send-api-put-request [url options]
  (client/put url options))

(defn send-api-post-request [url options]
  (client/post url options))


;; UTILITY FUNCTIONS 


(defn parse-response-body [response]
  (json/read-str (response :body) :key-fn keyword))

(defn format-query-params [query-params]
  (str
   "?"
   (reduce
    #(str %1 "&" %2)
    (for [kv query-params]
      (str (name (key kv)) "=" (val kv))))))

(defn get-url
  ([endpoint] (get-url endpoint nil))
  ([endpoint query-params]
   (str (get-env-data :OANDA_API_URL) endpoint (when query-params (format-query-params query-params)))))

(defn get-api-data
  ([endpoint] (get-api-data endpoint nil))
  ([endpoint query-params]
   (-> endpoint (get-url query-params) (send-api-get-request) (parse-response-body))))


;; ACCOUNT DATA FUNCTIONS


(defn get-accounts [] (get-api-data "accounts"))

(defn get-account-summary
  ([] (get-account-summary (get-env-data :OANDA_DEFAULT_ACCOUNT_ID)))
  ([account-id]
   (get-api-data (get-account-endpoint account-id "summary"))))

(defn get-account-instruments
  ([] (get-account-instruments (get-env-data :OANDA_DEFAULT_ACCOUNT_ID)))
  ([account-id]
   (get-api-data (get-account-endpoint account-id "instruments"))))

(defn get-candles
  ([instrument-name granularity count] (get-candles (get-env-data :OANDA_DEFAULT_ACCOUNT_ID) instrument-name granularity count))
  ([account-id instrument-name granularity count]
   (let [endpoint (get-account-endpoint account-id (str "instruments/" instrument-name "/candles"))
         query-params {:granularity granularity :count count}]
     (get-api-data endpoint query-params))))


;; GET CANDLES EXAMPLE 

;; (def eurusd-candles (get-candles "EUR_USD" "M5" 5))
;; (print eurusd-candles)


;; GET OPEN POSITIONS


(defn get-open-positions
  ([] (get-open-positions (get-env-data :OANDA_DEFAULT_ACCOUNT_ID)))
  ([account-id] (get-api-data (get-account-endpoint account-id "openPositions"))))


;; SEND ORDER FUNCTIONS


(defn make-post-order-body [instrument units]
  {:order {:instrument instrument :units units :timeInForce "FOK" :type "MARKET" :positionFill "DEFAULT"}})

(defn make-post-put-options [body]
  {:headers (get-headers)
   :content-type :json
   :body (json/write-str body)})

(defn send-post-order-request
  ([instrument units] (send-post-order-request (get-env-data :OANDA_DEFAULT_ACCOUNT_ID) instrument units))
  ([account-id instrument units]
   (send-api-post-request (get-url (get-account-endpoint account-id "orders")) (make-post-put-options (make-post-order-body instrument units)))))

;; (println (send-post-order-request "AUD_USD" 100))


;; CLOSE OPEN POSITION FOR INSTRUMENT


(defn close-position [instrument]
  (send-api-put-request
   (get-url
    (get-account-endpoint (str "positions/" instrument "/close")))
   (make-post-put-options {:longUnits "ALL"}))) ;; If position is short you need to exclude :longUnits and include :shortUnits *eye-roll*

(println (close-position "EUR_USD"))
