(ns v0_2_X.hydrate
  (:require
   [util :as util]
   [v0_2_X.strindicator :as strindy]
   [v0_2_X.config :as config]
   [v0_2_X.streams :as streams]))

(defn hydrate-strindy 
  ([strindy backtest-config] (hydrate-strindy strindy backtest-config nil))
  ([strindy backtest-config fore?]
  (let [streams (streams/fetch-formatted-streams backtest-config fore?)
        stream-proxy (-> streams :intention-streams first (util/subvec-end 10))
        sieve-stream (strindy/get-sieve-stream strindy (get streams :inception-streams))]
    {:id (.toString (java.util.UUID/randomUUID))
     :backtest-config (assoc backtest-config :stream-proxy stream-proxy)
     :strindy strindy
     :sieve-stream sieve-stream
     :return-stream (strindy/sieve->return sieve-stream (get streams :intention-streams))})))

(defn is-sieve-unique? [test-stream sieve-streams]
  (not (some #(= % test-stream) sieve-streams)))

(defn get-rand-hyst [backtest-config]
  (let [strindy (strindy/make-strindy (get backtest-config :strindy-config))]
    (hydrate-strindy strindy backtest-config false)))

(defn get-unique-hystrindies
  ([ga-config] (get-unique-hystrindies ga-config (get-in ga-config [:pop-config :pop-size])))
  ([ga-config num-strindies]
   (loop [v []]
     (if (< (count v) num-strindies)
       (recur
        (let [new-hystrindy (get-rand-hyst (get ga-config :backtest-config))
              new-sieve (get new-hystrindy :sieve-stream)
              prior-sieves (map :sieve-stream v)]
          (if (is-sieve-unique? new-sieve prior-sieves) (conj v new-hystrindy) v)))
       v))))

(defn get-hystrindy-fitness [hystrindy]
  (let [fitness (-> hystrindy :return-stream :beck last)]
    (assoc hystrindy :fitness fitness)))

(defn get-hystrindies-fitnesses [hystrindies]
  (for [hystrindy hystrindies]
    (get-hystrindy-fitness hystrindy)))

(defn get-init-pop [ga-config]
  (get-hystrindies-fitnesses (get-unique-hystrindies ga-config)))


(comment
  (def backtest-config (config/get-backtest-config-util
                      ;; ["EUR_USD" "both" "AUD_USD" "inception" "GBP_USD" "inception" "USD_JPY" "inception"]
                        ["EUR_USD" "intention"]
                        "ternary" 1 2 3 12 "H4"))

  (def streams (streams/fetch-formatted-streams backtest-config))

  (def strindy (strindy/make-strindy (backtest-config :strindy-config)))

  (def sieve-stream (strindy/get-sieve-stream strindy (streams :inception-streams)))

  (def return-stream (strindy/sieve->return sieve-stream (streams :intention-streams))))