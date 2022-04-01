(ns v0_2_X.factory
  (:require
   [v0_2_X.config :as config]
   [v0_2_X.ga :as ga]
   [v0_2_X.streams :as streams]
   [file :as file]))

(comment
  (do
    (def backtest-config (config/get-backtest-config-util
                          ["EUR_USD" "both" "AUD_USD" "both" "GBP_USD" "inception" "USD_JPY" "inception"]
                          "binary" 2 3 4 120 "M1"))

    (def ga-config (config/get-ga-config 25 backtest-config (config/get-pop-config 20 0.4 0.2 0.4)))

    (def streams (streams/fetch-formatted-streams backtest-config))

    (dotimes [n 3]
      (def best-pop (ga/run-epochs streams ga-config))

      (def candidate (first best-pop))

      (file/save-hystrindy-to-file (assoc candidate :return-stream (dissoc (get candidate :return-stream) :beck)) "hystrindies.edn"))))

(comment
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
                            stream-arg
                            "binary" 2 4 6 1200 "M1"))

      (def ga-config (config/get-ga-config 25 backtest-config (config/get-pop-config 40 0.4 0.3 0.5)))

      (def streams (streams/fetch-formatted-streams backtest-config))

      (dotimes [n 3]
        (def best-pop (ga/run-epochs streams ga-config))

        (def candidate (first best-pop))

        (file/save-hystrindy-to-file (assoc candidate :return-stream (dissoc (get candidate :return-stream) :beck)) "hystrindies.edn")))))