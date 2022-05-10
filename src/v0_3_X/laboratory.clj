(ns v0_3_X.laboratory
  (:require
   [v0_3_X.arena :as arena]
   [config :as config]
   [v0_2_X.hyst_factory :as factory]
   [clojure.core.async :as async]
   ))

(comment

  (def factory-config (config/get-factory-config-util
                       [["CAD_SGD" "inception" "AUD_CAD" "inception"
                         "AUD_CHF" "inception" "EUR_USD" "inception"
                         "EUR_JPY" "inception" "EUR_GBP" "inception"
                         "GBP_USD" "inception" "AUD_USD" "both"]
                        "ternary" 1 2 3 250 500 "M15" "score-x"]
                       [30 0.5 0.2 0.5]
                       10 20))
  (factory/run-factory factory-config))