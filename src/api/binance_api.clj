(ns api.binance_api
  (:require
   [env :as env]
   [api.util :as api-util]
   [clojure.data.json :as json]
   [api.headers :as headers]))

(defn get-candles [instrument-config]
  (api-util/get-binance-api-data "klines" instrument-config))

(defn format-candles [candles]
   (map
   (fn [candle]
     {:time (first candle)
      :open (Double/parseDouble (second candle))})
   candles))

(defn get-open-prices [instrument-config]
  (format-candles (get-candles instrument-config)))

(defn get-instrument-stream [instrument-config]
  (vec (for [data (get-open-prices instrument-config)] (get data :open))))


;; (defn send-order-request
;;   ([instrument units] (send-order-request (env/get-env-data :BINANCE_DEFAULT_ACCOUNT_ID) instrument units))
;;   ([account-id instrument units]
;;    (api-util/send-api-post-request 
;;     (api-util/build-oanda-url (get-account-endpoint account-id "orders")) 
;;     (make-request-options (make-post-order-body instrument units)))))


(comment
  (api-util/send-api-post-request (api-util/build-binance-url "order/test") {:symbol "BTCUSDT" :side "BUY" :type "MARKET" }))

(comment
  (def instrument-config (api-util/get-instrument-config "ETHBTC" "M30" 12))
  (get-open-prices instrument-config)
  (get-instrument-stream instrument-config)
  )

(comment
  (get-candles (api-util/get-instrument-config "ETHBTC" "M30" 10))
  )

(comment
  (api-util/get-binance-api-data "time")
  )

(comment 
  (map :symbol (:symbols (api-util/get-binance-api-data "exchangeInfo")))
  (api-util/get-binance-api-data "exchangeInfo" {:symbol "ETHBTC"})
  (api-util/get-binance-api-data "exchangeInfo" {:symbols "[\"ETHBTC\",\"LTCBTC\"]"})
)

(comment
  (api-util/get-binance-api-data "klines" {:symbol "ETHBTC" :interval "15m" :limit 10})
  )
