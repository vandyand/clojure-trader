(ns v0_1_X.oanda_api
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
  ([endpoint instrument-config]
   (str (get-env-data :OANDA_API_URL) endpoint (when instrument-config (format-query-params (dissoc instrument-config :name))))))

(defn get-api-data
  ([endpoint] (get-api-data endpoint nil))
  ([endpoint instrument-config]
   (-> endpoint (get-url instrument-config) (send-api-get-request) (parse-response-body))))

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
  ([instrument-config] (get-candles (get-env-data :OANDA_DEFAULT_ACCOUNT_ID) instrument-config))
  ([account-id instrument-config]
   (let [endpoint (get-account-endpoint account-id (str "instruments/" (get instrument-config :name) "/candles"))]
     (get-api-data endpoint instrument-config))))

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
   :body (json/write-str body)
   :as :json})

(defn send-order-request
  ([instrument units] (send-order-request (get-env-data :OANDA_DEFAULT_ACCOUNT_ID) instrument units))
  ([account-id instrument units]
   (send-api-post-request (get-url (get-account-endpoint account-id "orders")) (make-request-options (make-post-order-body instrument units)))))

;; CLOSE OPEN POSITION FOR INSTRUMENT

;; For our uses, we're going to rely heavily on close-trade function below and not close out entire positions.
;; The close-position functions are here in case they are needed at some point in the future

(defn close-position 
  ([instrument] (close-position instrument true))
  ([instrument long-pos?]
  (send-api-put-request
   (get-url
    (get-account-endpoint (str "positions/" instrument "/close")))
   (make-request-options (if long-pos? {:longUnits "ALL"} {:shortUnits "ALL"})))))

(defn close-long-position [instrument]
  (close-position instrument true))

(defn close-short-position [instrument]
  (close-position instrument false))

;; TRADES FUNCTIONS

(defn get-open-trades []
  (get-api-data (get-account-endpoint "openTrades")))

(defn get-open-trade [trade-id]
  (get-api-data (get-account-endpoint (str "trades/" trade-id))))

(defn close-trade [trade-id]
  (send-api-put-request
   (get-url (get-account-endpoint (str "trades/" trade-id "/close")))
   (make-request-options {:units "ALL"})))

;; CLIENT ID STUFF

(defn update-trade-with-id [trade-id client-id]
  (send-api-put-request
   (get-url (get-account-endpoint (str "trades/" trade-id "/clientExtensions")))
   (make-request-options {:clientExtensions {:id client-id}})))

(defn get-trade-client-id [trade-id]
  (-> trade-id
      get-open-trade
      :trade
      :clientExtensions
      :id))

(defn get-trade-by-client-id [client-id]
  (let [trades (:trades (get-open-trades))]
    (filter (fn [trade] (= client-id (-> trade :clientExtensions :id))) trades)))

(defn send-order-request-with-client-id [instrument units client-id]
  (let [trade-id (-> (send-order-request instrument units) :body :orderFillTransaction :id)]
    (Thread/sleep 100)
    (update-trade-with-id trade-id client-id)))

(defn close-trade-by-client-id [client-id]
  (let [trade-id (-> (get-trade-by-client-id client-id) first :id)]
    (Thread/sleep 100)
    (close-trade trade-id)))

(comment
  (get-open-trades)

  (close-position "EUR_USD")

  (send-order-request-with-client-id "EUR_USD" 17 "id-17")

  (get-trade-by-client-id "id-17")

  (for [n (range 1 10)]
    (send-order-request-with-client-id "EUR_USD" n (str "id-" n)))

  (close-trade-by-client-id "id-1")

  (for [n (range 2 10)]
    (close-trade-by-client-id (str "id-" n)))
  )