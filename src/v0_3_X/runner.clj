(ns v0_3_X.runner
  (:require
   [util :as util]
   [v0_2_X.config :as config]
   [v0_2_X.hyst_factory :as factory]
   [v0_3_X.arena :as arena]
   [clojure.core.async :as async]))


(comment
  (do
    (def backtest-config (config/get-backtest-config-util
                          ["BTCUSD" "both"]
                          "ternary" 2 3 4 500 50 "H1" "score-x"))

    (def ga-config (config/get-ga-config 10 backtest-config (config/get-pop-config 20 0.5 0.1 0.5)))

    (def factory-config (config/get-factory-config 3 ga-config))

    (factory/run-factory factory-config)
    
    ))


(comment
  (do
    (def backtest-config (config/get-backtest-config-util
                          ["EUR_USD" "inception" "AUD_USD" "inception" "GBP_USD" "inception"
                           "EUR_GBP" "inception" "USD_JPY" "both"]
                          "ternary" 2 4 6 2000 200 "M15" "score-x"))

    (def ga-config (config/get-ga-config 10 backtest-config (config/get-pop-config 10 0.4 0.2 0.4)))

    (def factory-config (config/get-factory-config 21 ga-config))

    (factory/run-factory factory-config)
  )
)

(comment
  (async/go-loop []
    (try (arena/run-arena ["M15-2000-eur_usd-aud_usd-gbp_usd-eur_gbp-Target_USD_JPY.edn"
                           "H4-2500-Target_EUR_USD-gbp_usd-eur_gbp.edn"
                           "H4-2500-eur_usd-Target_GBP_USD-eur_gbp.edn"
                           "H4-2500-eur_usd-gbp_usd-Target_EUR_GBP.edn"])
         (catch Throwable e
           (println "Error has been caught!" (.getMessage e))))
    (Thread/sleep 300000)
    (recur))
  )

(comment 
  (async/go
   
    (def backtest-config (config/get-backtest-config-util
                          ["EUR_USD" "inception" "AUD_USD" "both" "GBP_USD" "inception"
                           "EUR_GBP" "inception" "USD_JPY" "inception"]
                          "ternary" 2 3 4 2400 2400 "M15" "sharpe"))

    (def ga-config (config/get-ga-config 15 backtest-config (config/get-pop-config 100 0.4 0.2 0.4)))

    (def factory-config (config/get-factory-config 21 ga-config))

    (factory/run-factory factory-config)
   ))

(comment
  (async/go
    (try (arena/run-arena ["M15-2400-eur_usd-Target_AUD_USD-gbp_usd-eur_gbp-usd_jpy.edn"])
         (catch Throwable e
           (println "Error has been caught!" (.getMessage e)))))
  )