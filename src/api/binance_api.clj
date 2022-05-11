(ns api.binance_api
  (:require
   [env :as env]
   [api.util :as util]
   [clojure.data.json :as json]
   [api.headers :as headers]))

(defn get-candles [instrument-config]
  (util/get-binance-api-data "klines" instrument-config))

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


(comment
  (def instrument-config (util/get-instrument-config "ETHBTC" "M30" 12))
  (get-open-prices instrument-config)
  (get-instrument-stream instrument-config)
  )

(comment
  (get-candles (util/get-instrument-config "ETHBTC" "M30" 50))
  )

(comment
  (util/get-binance-api-data "time")
  )

(comment 
  (map :symbol (:symbols (util/get-binance-api-data "exchangeInfo")))
  (util/get-binance-api-data "exchangeInfo" {:symbol "ETHBTC"})
  (util/get-binance-api-data "exchangeInfo" {:symbols "[\"ETHBTC\",\"LTCBTC\"]"})
)

(comment
  (util/get-binance-api-data "klines" {:symbol "ETHBTC" :interval "15m" :limit 10})
  )
