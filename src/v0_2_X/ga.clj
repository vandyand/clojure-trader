(ns v0_2_X.ga
  (:require [clojure.pprint :as pp]
            [clojure.zip :as z]
            [v0_2_X.config :as config]
            [v0_2_X.hydrate :as hyd]
            [v0_2_X.strindicator :as strindy]
            [v0_2_X.oanda_strindicator :as ostrindy]))

(def backtest-config (config/get-backtest-config-util
                      ["EUR_USD" "both" "AUD_USD" "inception" "GBP_USD" "inception" "USD_JPY" "inception"]
                      "binary" 2 2 3 12 "H1"))
(def ga-config (config/get-ga-config 5 backtest-config (config/get-pop-config 20 0.5 0.4 0.4)))


(def strindy (strindy/make-strindy-recur (get backtest-config :strindy-config)))

(defn strindy-zip [strindy]
  (z/zipper
   (fn [x] (contains? x :inputs))
   (fn [x] (seq (get x :inputs)))
   (fn [node children]
     (assoc node :inputs (vec children)))
   strindy))


; get initial population with fitnesses

(defn get-hydrated-strindies 
  ([ga-config] (get-hydrated-strindies ga-config (get-in ga-config [:pop-config :pop-size])))
  ([ga-config num-strindies]
  (let [streams (hyd/get-backtest-streams (get ga-config :backtest-config))]
   (loop [i 0 v (transient [])]
     (if (< i num-strindies)
       (recur (inc i)
              (conj! v (hyd/get-hydrated-strindy (get-in ga-config [:backtest-config :strindy-config]) streams)))
       (persistent! v))))))

(def init-pop (get-hydrated-strindies ga-config))

; get best parents

; make children via mutation and crossover

; combine with parents to get new population with fitnesses

; repeat
