(ns arena.oanda_instrument
  (:require [arena.oanda_api :as oa]
            [incubator.strategy :as strat]
            [incubator.vec_strategy :as vat]
            ;; [clojure.pprint :as pp]
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
   (def eurusd-stream (vec (for [data (get-open-prices "EUR_USD" "H1" 5000)] (data :o))))
   (def eurusd (with-meta eurusd-stream {:name "eurusd"}))
   (def input-config (strat/get-input-config 10 (count eurusd) 0.005 1 0 100))
   (def tree-config (strat/get-tree-config 2 8 (vat/get-index-pairs (input-config :num-input-streams))))
   (def input-streams (strat/get-input-streams input-config))
   (def eurusd-delta (strat/get-stream-delta eurusd "eurusd delta"))
   (def zeroed-eurusd (with-meta (vec (for [price eurusd] (- price (first eurusd)))) {:name "zeroed eurusd"}))
   (def input-and-eurusd-streams {:input-streams input-streams :target-stream zeroed-eurusd :target-stream-delta eurusd-delta})
   (def ga-config (ga/get-ga-config 20 0.5 0.4 0.4 input-and-eurusd-streams input-config tree-config))
   (def init-pop (ga/get-init-pop ga-config))
   (def best-strats (ga/run-epochs 10 init-pop ga-config))
   (ga/plot-strats-with-input-target-streams (take 5 best-strats) input-and-eurusd-streams)
   (ga/get-strats-info (take 5 best-strats))))