(ns v0_3_X.runner
  (:require
   [util :as util]
   [v0_2_X.config :as config]
   [v0_2_X.hyst_factory :as factory]
   [v0_3_X.arena :as arena]))


(comment
  (do
    (def backtest-config (config/get-backtest-config-util
                          ["EUR_USD" "both" "AUD_USD" "inception" "GBP_USD" "inception" "EUR_GBP" "inception"
                           "USD_CHF" "inception" "USD_CAD" "inception" "USD_JPY" "inception"]
                          "ternary" 2 3 4 12 "H4"))

    (def ga-config (config/get-ga-config 10 backtest-config (config/get-pop-config 10 0.4 0.4 0.4)))

    (def factory-config (config/get-factory-config 19 ga-config))

    (factory/run-factory factory-config))
  )


(comment
  (do
    (def backtest-config (config/get-backtest-config-util
                          ["EUR_USD" "both" "AUD_USD" "both" "GBP_USD" "both" "EUR_GBP" "inception" "USD_JPY" "inception"]
                          "binary" 4 8 12 1200 "M30"))

    (def ga-config (config/get-ga-config 100 backtest-config (config/get-pop-config 200 0.4 0.2 0.4)))

    (def factory-config (config/get-factory-config 5 ga-config))

    (factory/run-factory factory-config)

    (println "sleeping... " (util/current-time-sec))
    
    (Thread/sleep (* 1000 60 30))
    
    (while true
      (println "running...  " (util/current-time-sec))
      (arena/run-arena)
      (Thread/sleep 30000))
    )
  )

(comment
  (while true
    (arena/run-arena)
    (Thread/sleep 30000))
  )

(comment
  (arena/run-arena)
  )