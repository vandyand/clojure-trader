(ns arena.oanda_api
  (:require [clj-http.client :as client]
            ;; [clojure.pprint :as pp]
            [clojure.data.json :as json]))

(defn get-sensative-data [keywd]
  ((json/read-str (slurp ".sensative.json") :key-fn keyword) keywd))

(defn get-env-data [keywd]
  ((json/read-str (slurp ".env.json") :key-fn keyword) keywd))

(defn get-headers [] {:Authorization (str "Bearer " (get-sensative-data :OANDA_API_KEY)) :Accept-Datetime-Format "UNIX"})

;; SEND REQUESTS

(defn send-api-get-request
  ([url] (client/get url {:headers (get-headers) :content-type :json})))

(defn send-api-put-request [url options]
  (client/put url options))

(defn send-api-post-request [url options]
  (client/post url options))


;; UTILITY FUNCTIONS 


(defn get-account-endpoint
  ([end] (get-account-endpoint (get-env-data :OANDA_DEFAULT_ACCOUNT_ID) end))
  ([account-id end]
   (str "accounts/" account-id "/" end)))

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


;; GET CANDLES


(defn get-candles
  ([instrument-name granularity count] (get-candles (get-env-data :OANDA_DEFAULT_ACCOUNT_ID) instrument-name granularity count))
  ([account-id instrument-name granularity count]
   (let [endpoint (get-account-endpoint account-id (str "instruments/" instrument-name "/candles"))
         query-params {:granularity granularity :count count}]
     (get-api-data endpoint query-params))))


;; GET OPEN POSITIONS


(defn get-open-positions
  ([] (get-open-positions (get-env-data :OANDA_DEFAULT_ACCOUNT_ID)))
  ([account-id] (get-api-data (get-account-endpoint account-id "openPositions"))))


;; SEND ORDER FUNCTIONS


(defn make-post-order-body [instrument units]
  {:order {:instrument instrument :units units :timeInForce "FOK" :type "MARKET" :positionFill "DEFAULT"}})

(defn make-request-options [body]
  {:headers (get-headers)
   :content-type :json
   :body (json/write-str body)})

(defn send-order-request
  ([instrument units] (send-order-request (get-env-data :OANDA_DEFAULT_ACCOUNT_ID) instrument units))
  ([account-id instrument units]
   (send-api-post-request (get-url (get-account-endpoint account-id "orders")) (make-request-options (make-post-order-body instrument units)))))


;; CLOSE OPEN POSITION FOR INSTRUMENT

;; For our uses, we're going to rely heavily on close-trade function below and not close out entire positions.
;; The close-position functiona are here in case they are needed at some point in the future


(defn close-position [instrument long-pos?]
  (send-api-put-request
   (get-url
    (get-account-endpoint (str "positions/" instrument "/close")))
   (make-request-options (if long-pos? {:longUnits "ALL"} {:shortUnits "ALL"}))))

(defn close-long-position [instrument]
  (close-position instrument true))

(defn close-short-position [instrument]
  (close-position instrument false))


;; TRADEES FUNCTIONS


(defn get-open-trades []
  (get-api-data (get-account-endpoint "openTrades")))

(defn get-open-trade [trade-id]
  (get-api-data (get-account-endpoint (str "trades/" trade-id))))

(defn close-trade [trade-id]
  (send-api-put-request
   (get-url (get-account-endpoint (str "trades/" trade-id "/close")))
   (make-request-options {:units "ALL"})))

(defn update-trade-with-id [trade-id client-id]
  (send-api-put-request
   (get-url (get-account-endpoint (str "trades/" trade-id "/clientExtensions")))
   (make-request-options {:clientExtensions {:id client-id}})))

(defn get-trade-id-from-order-response [response]
  (-> response :body (json/read-str) :orderFillTransaction :id))
