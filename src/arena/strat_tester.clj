(ns arena.strat_tester
  (:require [arena.oanda_api :as oa]
            [incubator.strategy :as strat]
            [incubator.vec_strategy :as vat]
            [incubator.ga :as ga]))

(defn format-candles [candles]
  (map
   (fn [candle] {:time (Double/parseDouble (candle :time))
                 :o (Double/parseDouble (get-in candle [:mid :o]))})
   candles))

(defn get-open-prices [instrument granularity count]
  (format-candles (:candles (oa/get-candles instrument granularity count))))

(time
 (do
   (def eurusd-stream (vec (for [data (get-open-prices "EUR_USD" "H1" 500)] (data :o))))
   (def eurusd (with-meta eurusd-stream {:name "eurusd"}))
   (def input-config (strat/get-inputs-config 20 (count eurusd) 0.005 1 0 100))
   (def tree-config (strat/get-tree-config 2 6 (vat/get-index-pairs (input-config :num-input-streams))))
   (def input-streams (strat/get-input-streams input-config))
   (def eurusd-delta (strat/get-stream-delta eurusd "eurusd delta"))
   (def zeroed-eurusd (with-meta (vec (for [price eurusd] (- price (first eurusd)))) {:name "zeroed eurusd"}))
   (def input-and-eurusd-streams {:input-streams input-streams :target-stream zeroed-eurusd :target-stream-delta eurusd-delta})
   (def ga-config (ga/get-ga-config 40 0.2 0.4 0.5 input-and-eurusd-streams input-config tree-config))
   (def init-pop (ga/get-init-pop ga-config))
   (def best-strats (ga/run-epochs 10 init-pop ga-config))))