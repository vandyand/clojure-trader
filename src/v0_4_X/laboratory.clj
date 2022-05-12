(ns v0_4_X.laboratory
  (:require
   [v0_3_X.arena :as arena]
   [config :as config]
   [file :as file]
   [v0_2_X.hyst_factory :as factory]
   [clojure.core.async :as async]
   [util :as util]
   [v0_3_X.gauntlet :as gaunt]
   ))

(defn parse-config-arg-ranges [config-arg-ranges]
  )

(defn run-lab [configs]
  (doseq [config configs]
    (let [factory-config (apply config/get-factory-config-util config)]
    (factory/run-factory factory-config)
    (arena/get-robustness (util/config->file-name factory-config)))))

(comment
  (async/go-loop []
    (let [factory-config (config/get-factory-config-util
                          [["USD_CAD" "both"]
                           "ternary" 1 2 2 250 250 "M15" "sharpe-per-std"]
                          [20 0.5 0.2 0.5]
                          0 20)
          robust-hysts (factory/run-checked-factory factory-config)]
      (arena/post-gausts (gaunt/run-gauntlet robust-hysts)))
    (Thread/sleep 280000)
    (recur))
  )


(comment
  (def factory-config (config/get-factory-config-util
                       [["AUD_JPY" "both"]
                        "ternary" 1 2 3 250 500 "M15" "score-x"]
                       [10 0.5 0.2 0.5]
                       0 10))
  (factory/run-factory factory-config)
  (arena/get-robustness (util/config->file-name factory-config))
  )


(comment

  ( ["EUR_JPY" "AUD_CAD"] 
           [[["ternary" "long-only" "short-only"]
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