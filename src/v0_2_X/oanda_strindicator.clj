(ns v0_2_X.oanda_strindicator
  (:require [v0_1_X.arena.oanda_api :as oa]
            [v0_1_X.arena.oanda_instrument :as oai]
            [v0_1_X.incubator.strategy :as strat]
            [v0_1_X.incubator.inputs :as inputs]
            ;; [clojure.pprint :as pp]
            [v0_1_X.incubator.ga :as ga]
            [v0_2_X.strindicator :as strindy]))

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

(defn get-instrument-stream [instrument-config] (vec (for [data (oai/get-open-prices  instrument-config)] (get data :o))))

(defn zero-stream [stream]
  (vec (for [price stream] (- price (first stream)))))

(def num-data-points 1000)
(def instrument-config (oai/get-instrument-config "EUR_USD" "H1" num-data-points))
(def input-config (strindy/get-strindy-input-config 10 1 num-data-points 0.005 1 0 100))
(def tree-config (strat/get-tree-config 2 8 (count (get input-config :inception-streams-config))))
(def pop-config (ga/get-pop-config 40 0.5 0.4 0.4))
(def ga-config (ga/get-ga-config 20 input-config tree-config pop-config))

(def eurusd (with-meta (get-instrument-stream instrument-config) {:name "eurusd"}))
(def eurusd-delta (strat/get-stream-delta eurusd "eurusd delta"))

(def best-strats (ga/run-epochs ga-config))
(ga/plot-strats-and-inputs (take 5 best-strats) input-config)
(ga/get-strats-info (take 5 best-strats))