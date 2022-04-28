(ns v0_3_X.runner
  (:require
   [v0_2_X.config :as config]
   [v0_2_X.hyst_factory :as factory]
   [v0_3_X.arena :as arena]))


(comment
  (do
    (def backtest-config (config/get-backtest-config-util
                          ["EUR_USD" "both" "AUD_USD" "both" "GBP_USD" "inception" "USD_JPY" "inception"]
                          "binary" 1 2 4 1200 "M1"))

    (def ga-config (config/get-ga-config 10 backtest-config (config/get-pop-config 200 0.4 0.3 0.5)))

    (def factory-config (config/get-factory-config 5 ga-config))

    (factory/run-factory factory-config)

    (Thread/sleep 90000)
    
    (while true
      (arena/run-arena)
      (Thread/sleep 30000)))
  )

(comment
  (while true
    (arena/run-arena)
    (Thread/sleep 30000))
  )

(comment
  (arena/run-arena)
  )