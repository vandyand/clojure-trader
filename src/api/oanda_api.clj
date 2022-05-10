(ns api.oanda_api
  (:require [clj-http.client :as client]
            ;; [clojure.pprint :as pp]
            [clojure.data.json :as json]
            [env :as env]
            [api.util :as util]
            [api.headers :as headers]))

;; UTILITY FUNCTIONS 

(defn get-account-endpoint
  ([end] (get-account-endpoint (env/get-env-data :OANDA_DEFAULT_ACCOUNT_ID) end))
  ([account-id end]
   (str "accounts/" account-id "/" end)))

;; ACCOUNT DATA FUNCTIONS

(defn get-accounts [] (util/get-oanda-api-data "accounts"))

(defn get-account-summary
  ([] (get-account-summary (env/get-env-data :OANDA_DEFAULT_ACCOUNT_ID)))
  ([account-id]
   (util/get-oanda-api-data (get-account-endpoint account-id "summary"))))

(defn get-account-instruments
  ([] (get-account-instruments (env/get-env-data :OANDA_DEFAULT_ACCOUNT_ID)))
  ([account-id]
   (util/get-oanda-api-data (get-account-endpoint account-id "instruments"))))

(defn account-instruments->names [account-instruments]
  (map (fn [instrument] (:name instrument)) (:instruments account-instruments)))

(defn get-account-instruments-names []
  (-> (get-account-instruments) account-instruments->names))

;; GET CANDLES

(defn get-candles
  ([instrument-config] (get-candles (env/get-env-data :OANDA_DEFAULT_ACCOUNT_ID) instrument-config))
  ([account-id instrument-config]
   (let [endpoint (get-account-endpoint account-id (str "instruments/" (get instrument-config :name) "/candles"))]
     (util/get-oanda-api-data endpoint instrument-config))))

;; GET OPEN POSITIONS

(defn get-open-positions
  ([] (get-open-positions (env/get-env-data :OANDA_DEFAULT_ACCOUNT_ID)))
  ([account-id] (util/get-oanda-api-data (get-account-endpoint account-id "openPositions"))))

;; SEND ORDER FUNCTIONS

(defn make-post-order-body [instrument units]
  {:order {:instrument instrument :units units :timeInForce "FOK" :type "MARKET" :positionFill "DEFAULT"}})

(defn make-request-options [body]
  {:headers (headers/get-oanda-headers)
   :content-type :json
   :body (json/write-str body)
   :as :json})

(defn send-order-request
  ([instrument units] (send-order-request (env/get-env-data :OANDA_DEFAULT_ACCOUNT_ID) instrument units))
  ([account-id instrument units]
   (util/send-api-post-request 
    (util/build-oanda-url (get-account-endpoint account-id "orders")) 
    (make-request-options (make-post-order-body instrument units)))))

;; OANDA STRINDICATOR STUFF

(defn format-candles [candles]
  (map
   (fn [candle]
     {:time (Double/parseDouble (get candle :time))
      :open (Double/parseDouble (get-in candle [:mid :o]))})
   candles))

(defn get-open-prices [instrument-config]
  (format-candles (get (get-candles instrument-config) :candles)))

(defn get-instrument-stream [instrument-config]
  (vec (for [data (get-open-prices instrument-config)] (get data :open))))

(defn get-instruments-streams [config]
 (let [instruments-config (util/get-instruments-config config)]
  (for [instrument-config instruments-config] 
    (get-instrument-stream instrument-config))))



;; CLOSE OPEN POSITION FOR INSTRUMENT

;; For our uses, we're going to rely heavily on close-trade function below and not close out entire positions.
;; The close-position functions are here in case they are needed at some point in the future

(defn close-position 
  ([instrument] (close-position instrument true))
  ([instrument long-pos?]
  (util/send-api-put-request
   (util/build-oanda-url
    (get-account-endpoint (str "positions/" instrument "/close")))
   (make-request-options (if long-pos? {:longUnits "ALL"} {:shortUnits "ALL"})))))

(defn close-long-position [instrument]
  (close-position instrument true))

(defn close-short-position [instrument]
  (close-position instrument false))

;; TRADES FUNCTIONS

(defn get-open-trades []
  (util/get-oanda-api-data  (get-account-endpoint "openTrades")))

(defn get-open-trade [trade-id]
  (util/get-oanda-api-data  (get-account-endpoint (str "trades/" trade-id))))

(defn close-trade [trade-id]
  (util/send-api-put-request
   (util/build-oanda-url (get-account-endpoint (str "trades/" trade-id "/close")))
   (make-request-options {:units "ALL"})))

;; CLIENT ID STUFF

(defn update-trade-with-id [trade-id client-id]
  (util/send-api-put-request
   (util/build-oanda-url (get-account-endpoint (str "trades/" trade-id "/clientExtensions")))
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

(comment
  (account-instruments->names (get-account-instruments))
  )
  