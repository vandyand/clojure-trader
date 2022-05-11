(ns v0_3_X.laboratory
  (:require
   [v0_3_X.arena :as arena]
   [config :as config]
   [v0_2_X.hyst_factory :as factory]
   [clojure.core.async :as async]
   [util :as util]
   ))

(defn parse-config-arg-ranges [config-arg-ranges]
  )

(defn run-lab [configs]
  (doseq [config configs]
    (let [factory-config (apply config/get-factory-config-util config)]
    (factory/run-factory factory-config)
    (arena/get-robustness (util/config->file-name factory-config)))))

(comment

  ( ["EUR_JPY" "AUD_CAD"] 
           [[["ternary" "binary"]
             [1 2 3] [2 4 6]]
            [[250 500]]
            ["M15" "M30" "H1"]
            ["balance" "sharpe" "sharpe-per-std" "inv-max-dd-period" "score-x"]
            [[25 0.5 0.2 0.5] [25 0.2 0.6 0.2] [25 0.2 0.1 0.7] [25 0.8 0.8 0.1] [25 0.8 0.2 0.6]]
            [10 20]
            5])
  
  (def factory-config (config/get-factory-config-util
                       [["CAD_SGD" "inception" "AUD_CAD" "inception"
                         "AUD_CHF" "inception" "EUR_USD" "inception"
                         "EUR_JPY" "inception" "EUR_GBP" "inception"
                         "GBP_USD" "inception" "AUD_USD" "both"]
                        "ternary" 1 2 3 250 500 "M15" "score-x"]
                       [30 0.5 0.2 0.5]
                       10 20))
  (factory/run-factory factory-config))