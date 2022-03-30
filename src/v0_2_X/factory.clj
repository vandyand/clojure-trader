(ns v0_2_X.factory
  (:require
   [v0_2_X.config :as config]
   [v0_2_X.ga :as ga]
   [v0_2_X.hydrate :as hyd]
   [file :as file]))
 
 (def backtest-config (config/get-backtest-config-util
                      ;; ["EUR_USD" "both" "AUD_USD" "inception" "GBP_USD" "inception" "USD_JPY" "inception" 
                      ;;  "EUR_GBP" "inception" "EUR_JPY" "inception" "USD_CHF" "inception" "AUD_JPY" "inception" 
                      ;;  "USD_CAD" "inception" "AUD_CAD" "inception" "CHF_JPY" "inception" "EUR_CHF" "inception" 
                      ;;  "NZD_USD" "inception" "EUR_CAD" "inception" "NZD_JPY" "inception" "AUD_CHF" "inception" 
                      ;;  "CAD_CHF" "inception" "GBP_CHF" "inception" "EUR_AUD" "inception" "GBP_CAD" "inception"]
                      ["EUR_USD" "both"]
                      "binary" 3 6 10 1200 "H1"))

(def ga-config (config/get-ga-config 20 backtest-config (config/get-pop-config 20 0.4 0.3 0.5)))

(def streams (hyd/get-backtest-streams (get ga-config :backtest-config)))

(file/save-streams-to-file streams)

(dotimes [n 5]
  (def best-pop (ga/run-epochs (dissoc streams :backtest-config) ga-config))

  (def candidate (first best-pop))
  
  (file/save-hystrindy-to-file candidate "hystrindies.edn")
  )
