(ns api.oanda_api
  (:require [clj-http.client :as client]
            ;; [clojure.pprint :as pp]
            [clojure.data.json :as json]
            [env :as env]
            [api.util :as util]
            [api.headers :as headers]))

;; UTILITY FUNCTIONS 

(defn get-account-endpoint
  ([end] (get-account-endpoint (env/get-account-id) end))
  ([account-id end]
   (str "accounts/" account-id "/" end)))

;; ACCOUNT DATA FUNCTIONS

(defn get-accounts [] (util/get-oanda-api-data "accounts"))

(defn get-account-summary
  ([] (get-account-summary (env/get-account-id)))
  ([account-id]
   (util/get-oanda-api-data (get-account-endpoint account-id "summary"))))

(defn get-account-balance
  ([] (get-account-balance (env/get-account-id)))
  ([account-id]
   (-> (get-account-summary account-id) :account :balance Double/parseDouble)))

(defn get-account-nav
  ([] (get-account-balance (env/get-account-id)))
  ([account-id]
   (-> (get-account-summary account-id) :account :NAV Double/parseDouble)))

(defn get-account-instruments
  ([] (get-account-instruments (env/get-account-id)))
  ([account-id]
   (util/get-oanda-api-data (get-account-endpoint account-id "instruments"))))

(defn account-instruments->names [account-instruments]
  (map (fn [instrument] (:name instrument)) (:instruments account-instruments)))

(defn get-account-instruments-names []
  (-> (get-account-instruments) account-instruments->names))

;; GET CANDLES

(defn get-api-candle-data
  ([instrument-config] (get-api-candle-data (env/get-account-id) instrument-config))
  ([account-id instrument-config]
   (let [endpoint (get-account-endpoint account-id (str "instruments/" (get instrument-config :name) "/candles"))]
     (util/get-oanda-api-data endpoint instrument-config))))

(comment 
  (get-api-candle-data {:name "AUD_JPY" :granularity "M1" :count 3})
  )

;; GET OPEN POSITIONS

(defn get-open-positions
  ([] (get-open-positions (env/get-account-id)))
  ([account-id] (util/get-oanda-api-data (get-account-endpoint account-id "openPositions"))))

;; SEND ORDER FUNCTIONS

(defn make-market-order-body [instrument units]
  {:order {:instrument instrument 
           :units units 
           :timeInForce "FOK" 
           :type "MARKET" 
           :positionFill "DEFAULT"}})

(defn make-market-price-order-body [instrument units price-bound]
  {:order {:instrument instrument 
           :units units 
           :timeInForce "FOK" 
           :type "MARKET" 
           :positionFill "DEFAULT"
           :priceBound price-bound}})

(defn make-limit-sltp-order-body [instrument units details]
  {:order {:instrument instrument
           :units units
           :price (details :price)
           :timeInForce "GTD"
           :gtdTime (details :cancel-time) 
           :triggerCondition "DEFAULT"
           :type "LIMIT"
           :positionFill "DEFAULT"
           :stopLossOnFill {:price (details :sl-price)}
           :takeProfitOnFill {:price (details :tp-price)}}})

(defn make-limit-order-details [cancel-time price tp-price sl-price]
  {:order-type "LIMIT" :cancel-time (str cancel-time) :price (str price) :tp-price (str tp-price) :sl-price (str sl-price)})

(defn make-request-options [body]
  {:headers (headers/get-oanda-headers)
   :content-type :json
   :body (json/write-str body)
   :as :json})

(defn send-order-request
  ([instrument units] (send-order-request instrument units "MARKET" 0))
  ([instrument units  order-type sltp-distance] (send-order-request instrument units order-type sltp-distance (env/get-account-id)))
  ([instrument units order-type sltp-distance account-id]
   (util/send-api-post-request 
    (util/build-oanda-url (get-account-endpoint account-id "orders")) 
    (make-request-options (if (= order-type "MARKET")
                            (make-market-order-body instrument units)
                            (make-limit-sltp-order-body instrument units sltp-distance))))))

(comment
  ;; 2022-07-06T18:51:00Z
  (send-order-request "EUR_USD" 100 {:order-type "LIMIT" :cancel-time "1657133757" 
                                     :price "1.0181" :tp-price "1.0201" :sl-price "1.0161"})
  
  (send-order-request "EUR_USD" 100 {:order-type "MARKET"})
  )

;; OANDA STRINDICATOR STUFF

(defn format-candles [candles]
  (map
   (fn [candle]
     {:time (Double/parseDouble (get candle :time))
      :open (Double/parseDouble (get-in candle [:mid :o]))})
   candles))

(defn get-open-prices [instrument-config]
  (format-candles (get (get-api-candle-data instrument-config) :candles)))

(defn get-instrument-stream-depreciated [instrument-config]
  (vec (for [data (get-open-prices instrument-config)] (get data :open))))

(defn get-instrument-stream [instrument-config]
  (let [api-data (get-api-candle-data instrument-config)]
    (vec
     (for [candle (get api-data :candles)]
       {:v (get candle :volume)
        :o (Double/parseDouble (get-in candle [:mid :o]))
        :h (Double/parseDouble (get-in candle [:mid :h]))
        :l (Double/parseDouble (get-in candle [:mid :l]))
        :c (Double/parseDouble (get-in candle [:mid :c]))}))))

(comment 
  (get-instrument-stream {:name "AUD_JPY" :granularity "M1" :count 3})
  )

(defn get-instruments-streams [config]
 (let [instruments-config (util/get-instruments-config config)]
  (for [instrument-config instruments-config] 
    (get-instrument-stream instrument-config))))



;; CLOSE OPEN POSITION FOR INSTRUMENT

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
  
  (get-account-summary)
  
  (get-account-balance)
  
  (get-open-trades)

  (close-long-position "USD_JPY")
  (close-short-position "USD_JPY")

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
  