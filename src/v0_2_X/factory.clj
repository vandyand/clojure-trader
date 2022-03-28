(ns v0_2_X.factory
  (:require
   [v0_2_X.config :as config]
   [v0_2_X.ga :as ga]
   [v0_2_X.hydrate :as hyd]
   [edn]))


 
 (def backtest-config (config/get-backtest-config-util
                      ;; ["EUR_USD" "both" "AUD_USD" "inception" "GBP_USD" "inception" "USD_JPY" "inception"]
                      ["EUR_USD" "intention"]
                      "binary" 1 2 3 10 "H1"))

(def ga-config (config/get-ga-config 10 backtest-config (config/get-pop-config 20 0.4 0.3 0.5)))

(def streams (hyd/get-backtest-streams (get ga-config :backtest-config)))

(edn/save-streams-to-file streams)

(dotimes [n 5]
  (def best-pop (ga/run-epochs (dissoc streams :backtest-config) ga-config))

  (def candidate (first best-pop))

  (edn/save-hystrindy-to-file candidate))
