(ns v0_2_X.ga
  (:require [clojure.pprint :as pp]
            [clojure.zip :as z]
            [v0_2_X.config :as config]
            [v0_2_X.populate :as populate]
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

(-> strindy (strindy-zip) (z/down) (z/right))

; get initial population with fitnesses

; get best parents

; make children via mutation and crossover

; combine with parents to get new population with fitnesses

; repeat
