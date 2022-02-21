(ns v0_1_X.arena.oanda_instrument
  (:require [v0_1_X.arena.oanda_api :as oa]
            [v0_1_X.incubator.strategy :as strat]
            [v0_1_X.incubator.inputs :as inputs]
            ;; [clojure.pprint :as pp]
            [v0_1_X.incubator.ga :as ga]))

(defn format-candles [candles]
  (map
   (fn [candle]
     {:time (Double/parseDouble (get candle :time))
      :o (Double/parseDouble (get-in candle [:mid :o]))})
   candles))

(defn get-instrument-config [name granularity count]
  {:name name :granularity granularity :count count})

(defn get-open-prices [instrument-config]
  (format-candles (get (oa/get-candles instrument-config) :candles)))

(defn get-stream-from-instrument-by-key [instrument-config target-key]
  (vec
   (for [data (get-open-prices instrument-config)]
     (get data target-key))))

(defn get-instrument-streams [instrument-config]
  (map #(get-stream-from-instrument-by-key instrument-config %) [:o :time]))

;; (def instrument-config (get-instrument-config "EUR_USD" "S5" 5))

;; (def instrument-streams (get-instrument-streams instrument-config))


(defn zero-stream [stream]
  (vec (for [price stream] (- price (first stream)))))

(def instrument-config (get-instrument-config "EUR_USD" "H1" 5000))
(def eurusd-stream (vec (for [data (get-open-prices  instrument-config)] (get data :o))))
(def eurusd (with-meta eurusd-stream {:name "eurusd"}))
(def input-config (inputs/get-sine-inputs-config 10 1 (count eurusd) 0.005 1 0 100))
(def tree-config (strat/get-tree-config 2 8 (strat/get-index-pairs (count (get input-config :inception-streams-config)))))
  ;;  (def input-streams (strat/get-input-streams input-config))
(def eurusd-delta (strat/get-stream-delta eurusd "eurusd delta"))
  ;;  (def input-and-eurusd-streams {:input-streams input-streams :intention-stream (with-meta (zero-stream eurusd-stream) {:name "zeroed target"}) :intention-stream-delta eurusd-delta})
(def pop-config (ga/get-pop-config 40 0.5 0.4 0.4))
(def ga-config (ga/get-ga-config 20 input-config tree-config pop-config))
(def best-strats (ga/run-epochs ga-config))
(ga/plot-strats-and-inputs (take 5 best-strats) input-config)
(ga/get-strats-info (take 5 best-strats))