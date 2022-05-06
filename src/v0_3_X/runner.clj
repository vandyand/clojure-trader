(ns v0_3_X.runner
  (:require
   [util :as util]
   [v0_2_X.config :as config]
   [v0_2_X.hyst_factory :as factory]
   [v0_3_X.arena :as arena]))


(comment
  (do
    (def backtest-config (config/get-backtest-config-util
                          ["EUR_USD" "both" "GBP_USD" "inception" "EUR_GBP" "inception"]
                          "ternary" 2 3 4 2500 250 "H4" "sharpe"))

    (def ga-config (config/get-ga-config 15 backtest-config (config/get-pop-config 100 0.8 0.1 0.7)))

    (def factory-config (config/get-factory-config 11 ga-config))

    (factory/run-factory factory-config)


    (def backtest-config (config/get-backtest-config-util
                          ["EUR_USD" "inception" "GBP_USD" "both" "EUR_GBP" "inception"]
                          "ternary" 2 3 4 2500 250 "H4" "sharpe"))

    (def ga-config (config/get-ga-config 15 backtest-config (config/get-pop-config 100 0.8 0.1 0.7)))

    (def factory-config (config/get-factory-config 11 ga-config))

    (factory/run-factory factory-config)


    (def backtest-config (config/get-backtest-config-util
                          ["EUR_USD" "inception" "GBP_USD" "inception" "EUR_GBP" "both"]
                          "ternary" 2 3 4 2500 250 "H4" "sharpe"))

    (def ga-config (config/get-ga-config 15 backtest-config (config/get-pop-config 100 0.8 0.1 0.7)))

    (def factory-config (config/get-factory-config 11 ga-config))

    (factory/run-factory factory-config)

    (while true
      (try
        (Thread/sleep 600000)
        (arena/run-arena ["H4-2500-Target_EUR_USD-gbp_usd-eur_gbp.edn"
                          "H4-2500-eur_usd-Target_GBP_USD-eur_gbp.edn"
                          "H4-2500-eur_usd-gbp_usd-Target_EUR_GBP.edn"])
        (catch Throwable e
          (println "Error has been caught!" (.getMessage e)))))))

(comment
  (arena/run-arena ["S30-50-Target_EUR_USD.edn"
                    "S30-50-Target_AUD_USD.edn"])
  )

(comment
 (do
  (arena/run-best-gausts "S30-50-Target_EUR_USD.edn")
  (arena/run-best-gausts "S30-50-Target_AUD_USD.edn"))
  
  )

(comment
  (do
    (def backtest-config (config/get-backtest-config-util
                          ["EUR_USD" "inception" "AUD_USD" "inception" "GBP_USD" "inception"
                           "EUR_GBP" "both" "USD_JPY" "inception"]
                          "binary" 4 8 12 1200 120 "M5"))

    (def ga-config (config/get-ga-config 100 backtest-config (config/get-pop-config 200 0.4 0.2 0.4)))

    (def factory-config (config/get-factory-config 5 ga-config))

    (factory/run-factory factory-config)

    (println "sleeping... " (util/current-time-sec))

    (Thread/sleep (* 1000 60 30))

    (while true
      (println "running...  " (util/current-time-sec))
      (arena/run-best-gaust)
      (Thread/sleep 30000))))

(comment
  (while true
    (try (arena/run-arena ["M5-50-EUR_USD-aud_usd-gbp_usd-eur_gbp-usd_chf-usd_cad-usd_jpy.edn"
                           "M10-50-eur_usd-AUD_USD-gbp_usd-eur_gbp-usd_chf-usd_cad-usd_jpy.edn"])
         (Thread/sleep (* 1000 600)) ;; last arg is seconds of pause
         (catch Throwable e
           (println "Error has been caught!" (.getMessage e))))))

(comment
  (arena/run-arena ["M5-50-EUR_USD-aud_usd-gbp_usd-eur_gbp-usd_chf-usd_cad-usd_jpy.edn"
                           "M10-50-eur_usd-AUD_USD-gbp_usd-eur_gbp-usd_chf-usd_cad-usd_jpy.edn"])
  )

(comment
  (try (arena/run-arena ["M10-50-eur_usd-AUD_USD-gbp_usd-eur_gbp-usd_chf-usd_cad-usd_jpy.edn"])
       (catch Throwable e
         (println "Error has been caught!" (.getMessage e))))
  )