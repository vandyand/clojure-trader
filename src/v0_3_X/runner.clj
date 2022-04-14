(ns v0_3_X.runner
  (:require
   [v0_2_X.config :as config]
   [v0_2_X.hyst_factory :as factory]
   [v0_3_X.arena :as arena]))


(comment
  (do
    (def backtest-config (config/get-backtest-config-util
                          ["EUR_USD" "both" "AUD_USD" "both" "GBP_USD" "inception" "USD_JPY" "inception"]
                          "binary" 3 6 10 1200 "M15"))

    (def ga-config (config/get-ga-config 100 backtest-config (config/get-pop-config 100 0.4 0.3 0.5)))

    (def factory-config (config/get-factory-config 7 ga-config))

    (factory/run-factory factory-config)

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