(ns v0_3_X.runner
  (:require
   [util :as util]
   [config :as config]
   [v0_2_X.hyst_factory :as factory]
   [v0_3_X.arena :as arena]
   [clojure.core.async :as async]))

(defn run-runner [runner-file-names _delay]
  (async/go-loop []
    (try (arena/run-arena runner-file-names)
         (catch Throwable e
           (println "Error has been caught!" (.getMessage e))))
    (Thread/sleep _delay)
    (recur)
  ))

;; AUD_CAD CAD_CHF AUD_CHF CAD_SGD
(comment
  (def factory-config (config/get-factory-config-util
                       [["CAD_SGD" "inception" "AUD_CAD" "inception"
                         "AUD_CHF" "inception" "EUR_USD" "inception"
                         "EUR_JPY" "inception" "EUR_GBP" "inception"
                         "GBP_USD" "inception" "AUD_USD" "both"]
                        "ternary" 1 2 3 250 500 "M15" "score-x"]
                       [30 0.5 0.2 0.5]
                       10 20))
  (factory/run-factory factory-config)
  (run-runner [(util/backtest-config->file-name (:backtest-config factory-config))] 30000)
  ;; (run-runner ["M15-250-CAD_SGD-AUD_CAD-AUD_CHF-EUR_USD-EUR_JPY-EUR_GBP-GBP_USD-T_AUD_USD.edn"] 30000)
  )

(comment
  ;; (arena/run-best-gausts "M15-2000-#EUR_USD.edn")
  (run-runner ["M15-200-T_CAD_SGD-AUD_CAD-CAD_CHF-AUD_CHF.edn"] 30000)
  (run-runner ["M15-200-CAD_SGD-T_AUD_CAD-CAD_CHF-AUD_CHF.edn"] 30000)
  (run-runner ["M15-200-CAD_SGD-AUD_CAD-T_CAD_CHF-AUD_CHF.edn"] 30000)
  (run-runner ["M15-200-CAD_SGD-AUD_CAD-CAD_CHF-T_AUD_CHF.edn"] 30000)
  (run-runner ["M15-200-CAD_SGD-AUD_CAD-CAD_CHF-AUD_CHF-T_EUR_CHF.edn"] 30000)
  (run-runner ["M15-250-CAD_SGD-AUD_CAD-CAD_CHF-AUD_CHF-EUR_CHF-T_EUR_USD.edn"] 30000)
  )

(comment
  (async/go
    (factory/run-many-factories
     ["EUR_USD" "AUD_USD" "GBP_USD"]
     [[nil "ternary" 2 3 4 100 20 "M15" "score-x"]
      [20 0.4 0.1 0.6] 10 3]))

  (factory/run-many-factories
   ["EUR_USD" "AUD_USD" "GBP_USD"]
   [[nil "ternary" 2 4 6 2000 200 "M15" "score-x"]
    [30 0.4 0.1 0.6] 10 21])
  )

(comment
  (do
    (def backtest-config (config/get-backtest-config-util
                          ["ETHBTC" "both"]
                          "ternary" 2 3 4 500 50 "H1" "score-x"))

    (def ga-config (config/get-ga-config 10 backtest-config (config/get-pop-config 20 0.5 0.1 0.5)))

    (def factory-config (config/get-factory-config 3 ga-config))

    (factory/run-factory factory-config)
    
    ))

(comment
  (async/go
    (def backtest-config (config/get-backtest-config-util
                          ["EUR_USD" "both" "AUD_USD" "inception" "GBP_USD" "inception"
                           "EUR_GBP" "inception" "USD_JPY" "inception" "EUR_JPY" "inception" 
                           "AUD_JPY" "inception"]
                          "ternary" 2 4 6 2000 200 "M15" "score-x"))

    (def ga-config (config/get-ga-config 10 backtest-config (config/get-pop-config 30 0.4 0.2 0.4)))

    (def factory-config (config/get-factory-config 21 ga-config))

    (factory/run-factory factory-config)
   
   (loop []
     (try (arena/run-arena ["M15-2000-target_eur_usd-aud_usd-gbp_usd-eur_gbp-usd_jpy-eur_jpy-aud_jpy.edn"])
         (catch Throwable e
           (println "Error has been caught!" (.getMessage e))))
    (Thread/sleep 300000)
    (recur))
  )
)



(comment
  (async/go-loop []
    (try (arena/run-arena ["M15-2000-#EUR_USD-AUD_USD-GBP_USD-EUR_GBP-USD_JPY-USD_CHF.edn"
                           "M15-2000-EUR_USD-#AUD_USD-GBP_USD-EUR_GBP-USD_JPY-USD_CHF.edn"
                           "M15-2000-EUR_USD-AUD_USD-#GBP_USD-EUR_GBP-USD_JPY-USD_CHF.edn"
                           "M15-2000-EUR_USD-AUD_USD-GBP_USD-EUR_GBP-USD_JPY-#USD_CHF.edn"])
         (catch Throwable e
           (println "Error has been caught!" (.getMessage e))))
    (Thread/sleep 300000)
    (recur))
  )

(comment
  (async/go-loop []
    (try (arena/run-arena ["M15-2000-eur_usd-aud_usd-gbp_usd-eur_gbp-Target_USD_JPY.edn"
                           "M15-2000-eur_usd-aud_usd-gbp_usd-eur_gbp-usd_jpy-Target_EUR_JPY.edn"
                           "M15-2000-eur_usd-aud_usd-gbp_usd-eur_gbp-usd_jpy-eur_jpy-Target_AUD_JPY.edn"])
         (catch Throwable e
           (println "Error has been caught!" (.getMessage e))))
    (Thread/sleep 300000)
    (recur))
  )

(comment
  (async/go-loop []
    (try (arena/run-arena ["M15-2000-Target_EUR_USD-aud_usd-gbp_usd.edn"])
         (catch Throwable e
           (println "Error has been caught!" (.getMessage e))))
    (Thread/sleep 300000)
    (recur))
  )

(comment 
  (async/go
   
    (def backtest-config (config/get-backtest-config-util
                          ["EUR_USD" "inception" "AUD_USD" "inception" "GBP_USD" "inception"
                           "EUR_GBP" "both" "USD_JPY" "inception" "USD_CHF" "inception"]
                          "ternary" 2 3 4 2000 200 "M15" "score-x"))

    (def ga-config (config/get-ga-config 15 backtest-config (config/get-pop-config 20 0.4 0.2 0.4)))

    (def factory-config (config/get-factory-config 21 ga-config))

    (factory/run-factory factory-config)
   ))

(comment
  (let [file-names ["H1-500-Target_ETHBTC.edn"]]
    (async/go
      (try (arena/run-arena file-names)
           (catch Throwable e
             (println "Error has been caught!" (.getMessage e))))))
  )


(comment
  (def pairs ["EUR_USD" "AUD_USD" "GBP_USD" "USD_JPY" "EUR_GBP" "EUR_JPY"
               "USD_CHF" "AUD_JPY" "USD_CAD" "AUD_CAD" "CHF_JPY" "EUR_CHF"
               "NZD_USD" "EUR_CAD" "NZD_JPY" "AUD_CHF" "CAD_CHF" "GBP_CHF"
               "EUR_AUD" "GBP_CAD"])
  )