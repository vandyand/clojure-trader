(ns v0_2_X.factory
  (:require
   [v0_2_X.config :as config]
   [v0_2_X.ga :as ga]
   [v0_2_X.hydrate :as hyd]
   [file :as file]))
 
 (def cpairs ["EUR_USD" "AUD_USD" "GBP_USD" "USD_JPY" "EUR_GBP" "EUR_JPY" 
              "USD_CHF" "AUD_JPY" "USD_CAD" "AUD_CAD" "CHF_JPY" "EUR_CHF" 
              "NZD_USD" "EUR_CAD" "NZD_JPY" "AUD_CHF" "CAD_CHF" "GBP_CHF" 
              "EUR_AUD" "GBP_CAD"])
 
 (def stream-args
   (for [n (range (count cpairs))]
     (assoc (conj (vec (interpose "inception" cpairs)) "inception") (-> n (* 2) (+ 1)) "both")))
 
(for [stream-arg stream-args]
 (do
   (def backtest-config (config/get-backtest-config-util
                      ;; ["EUR_USD" "inception" "AUD_USD" "both" "GBP_USD" "inception" "USD_JPY" "inception" 
                      ;;  "EUR_GBP" "inception" "EUR_JPY" "inception" "USD_CHF" "inception" "AUD_JPY" "inception" 
                      ;;  "USD_CAD" "inception" "AUD_CAD" "inception" "CHF_JPY" "inception" "EUR_CHF" "inception" 
                      ;;  "NZD_USD" "inception" "EUR_CAD" "inception" "NZD_JPY" "inception" "AUD_CHF" "inception" 
                      ;;  "CAD_CHF" "inception" "GBP_CHF" "inception" "EUR_AUD" "inception" "GBP_CAD" "inception"]
                      ;; ["EUR_USD" "both"]
                         stream-arg
                         "binary" 1 2 3 120 "M5"))

   (def ga-config (config/get-ga-config 10 backtest-config (config/get-pop-config 20 0.4 0.3 0.5)))

   (def streams (hyd/get-backtest-streams (get ga-config :backtest-config)))

   (file/save-streams-to-file streams)

   (dotimes [n 1]
     (def best-pop (ga/run-epochs (dissoc streams :backtest-config) ga-config))

     (def candidate (first best-pop))

     (file/save-hystrindy-to-file candidate "hystrindies.edn"))))
