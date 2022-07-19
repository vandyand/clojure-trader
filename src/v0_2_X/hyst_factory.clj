(ns v0_2_X.hyst_factory
  (:require [config :as config]
            [file :as file]
            [v0_2_X.ga :as ga]
            [v0_2_X.streams :as streams]
            [v0_3_X.gauntlet :as gaunt]
            [clojure.core.async :as async]
            [util :as util]))

(defn run-factory-to-file-async
  "Writes hysts to file"
  [factory-config file-chan watcher-atom]
  (file/open-file-writer-async
   file-chan
   (str file/data-folder file/hyst-folder (util/config->file-name factory-config))
   watcher-atom)
  (let [streams (streams/fetch-formatted-streams (-> factory-config :backtest-config))]
    (dotimes [n (-> factory-config :factory-num-produced)]
      (async/go
        (let [best-pop (ga/run-epochs streams factory-config)
              candidate (first best-pop)] ;; Update to get multiple candidates from one GA?
          (async/>!
           file-chan
           (file/format-hyst-for-edn
            (assoc candidate :return-stream (dissoc (get candidate :return-stream) :beck)))))))))

(defn run-factory-to-file
  "Writes hysts to file"
  ([factory-config]
   (let [streams (streams/fetch-formatted-streams (-> factory-config :backtest-config))]
     (dotimes [n (-> factory-config :factory-num-produced)]
      ;;  (println "factory num: " n)
       (let [best-pop (ga/run-epochs streams factory-config)
             candidate (first best-pop)] ;; Update to get multiple candidates from one GA?
         (file/save-hystrindy-to-file 
          (assoc candidate :return-stream (dissoc (get candidate :return-stream) :beck))))))))

(defn run-factory
  "Returns vector of length :factory-num-produced of 'good' hysts"
  ([factory-config]
   (let [streams (streams/fetch-formatted-streams (-> factory-config :backtest-config))]
     (loop [v (transient [])]
       (if (>= (count v) (:factory-num-produced factory-config))
         (persistent! v)
         (let [best-pop (ga/run-epochs streams factory-config)
               candidate (assoc (first best-pop) :return-stream
                                (dissoc (get (first best-pop) :return-stream) :beck))]
             (recur (conj! v candidate))))))))

(defn run-factory-async
  "Returns vector of length :factory-num-produced of 'good' hysts"
  ([factory-config factory-chan]
   (let [streams (streams/fetch-formatted-streams (-> factory-config :backtest-config))]
     (async/go-loop [v (transient [])]
       (if (>= (count v) (:factory-num-produced factory-config))
         (async/>! factory-chan (persistent! v))
         (let [best-pop (ga/run-epochs streams factory-config)
               candidate (assoc (first best-pop) :return-stream
                                (dissoc (get (first best-pop) :return-stream) :beck))]
             (recur (conj! v candidate))))))))

(defn run-checked-factory
  "Returns vector of length :factory-num-produced of 'good' hysts"
  ([factory-config]
   (let [streams (streams/fetch-formatted-streams (-> factory-config :backtest-config))]
     (loop [v (transient [])]
       (if (>= (count v) (:factory-num-produced factory-config))
         (persistent! v)
         (let [best-pop (ga/run-epochs streams factory-config)
               candidate (assoc (first best-pop) :return-stream
                                (dissoc (get (first best-pop) :return-stream) :beck))
               checked-candidate (when (gaunt/good-gaust? (gaunt/run-gauntlet-single candidate)) candidate)]
           (if checked-candidate
             (recur (conj! v checked-candidate))
             (recur v))))))))

(defn pairs->stream-args [pairs]
  (for [n (range (count pairs))]
    (assoc (conj (vec (interpose "inception" pairs)) "inception") (-> n (* 2) (+ 1)) "both")))

(defn run-many-factories [pairs factory-config-util-args]
  (let [streams-args (pairs->stream-args pairs)]
    (doseq [stream-args streams-args]
      (let [factory-config-args (assoc-in factory-config-util-args [0 0] stream-args)
            factory-config (apply config/get-factory-config-util factory-config-args)]
        (run-factory-to-file factory-config)))))


(comment
  (do
    (def backtest-config (config/get-backtest-config-util
                          ["EUR_USD" "both" "AUD_USD" "inception" "GBP_USD" "inception" "USD_JPY" "inception"]
                          "ternary" 2 3 3 120 "H4" "sharpe"))

    (def ga-config (config/get-ga-config 12 backtest-config (config/get-pop-config 30 0.4 0.4 0.4)))

    (def factory-config (config/get-factory-config 3 ga-config))

    (run-factory-to-file factory-config)))

(comment
  (do
    (def backtest-config (config/get-backtest-config-util
                          ["EUR_USD" "both" "AUD_USD" "both" "GBP_USD" "inception" "USD_JPY" "inception"]
                          "long-only" 2 3 4 1200 "M5"))

    (def ga-config (config/get-ga-config 12 backtest-config (config/get-pop-config 30 0.4 0.2 0.4)))

    (def streams (streams/fetch-formatted-streams backtest-config))

    (dotimes [n 2]
      (def best-pop (ga/run-epochs streams ga-config))

      (def candidate (first best-pop))

      (file/save-hystrindy-to-file (assoc candidate :return-stream (dissoc (get candidate :return-stream) :beck))
                                   "hystrindies.edn"))))



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
                            "long-only" 2 4 6 1200 "H2"))

      (def ga-config (config/get-ga-config 25 backtest-config (config/get-pop-config 40 0.4 0.3 0.5)))

      (def streams (streams/fetch-formatted-streams backtest-config))

      (dotimes [n 3]
        (def best-pop (ga/run-epochs streams ga-config))

        (def candidate (first best-pop))

        (file/save-hystrindy-to-file (assoc candidate :return-stream (dissoc (get candidate :return-stream) :beck)) "hystrindies.edn")))))