(ns v0_2_X.hystrindy
  (:require
   [util :as util]
   [v0_2_X.strindicator :as strindy]
   [v0_2_X.nean_strindy :as nindy]
   [config :as config]
   [v0_2_X.streams :as streams]
   [stats :as stats]
   [helpers :as hlp]))

(defn hydrate-strindy 
  ([strindy backtest-config streams]
  (let [stream-proxy (mapv :o (-> streams :inception-streams first (util/subvec-end 10)))
        sieve-stream (nindy/get-sieve-stream strindy (get streams :inception-streams))]
    {:id (.toString (java.util.UUID/randomUUID))
     :backtest-config (assoc backtest-config :stream-proxy stream-proxy)
     :strindy strindy
     :sieve-stream sieve-stream
     :return-stream (nindy/sieve->return sieve-stream (get streams :intention-streams))})))

(defn is-sieve-unique? [test-stream sieve-streams]
  (not (some #(= % test-stream) sieve-streams)))

(defn get-rand-hyst [backtest-config streams]
  (let [strindy (strindy/make-strindy (get backtest-config :strindy-config))]
    (hydrate-strindy strindy backtest-config streams)))

(defn get-unique-hystrindies
  ([ga-config streams] (get-unique-hystrindies ga-config streams (get-in ga-config [:pop-config :pop-size])))
  ([ga-config streams num-strindies]
   (loop [v []]
     (if (< (count v) num-strindies)
       (recur
        (let [new-hystrindy (get-rand-hyst (get ga-config :backtest-config) streams)
              new-sieve (get new-hystrindy :sieve-stream)
              prior-sieves (map :sieve-stream v)]
          (if (is-sieve-unique? new-sieve prior-sieves) (conj v new-hystrindy) v)))
       v))))

(defn get-hystrindy-fitness [hystrindy]
  (let [fitness-type (get-in hystrindy [:backtest-config :fitness-type])
        fitness (cond (= fitness-type "balance") (-> hystrindy :return-stream :beck stats/balance)
                      (= fitness-type "sharpe") (-> hystrindy :return-stream :rivulet stats/sharpe)
                      (= fitness-type "sharpe-per-std") (-> hystrindy :return-stream :rivulet stats/sharpe-per-std)
                      (= fitness-type "inv-dd-period") (-> hystrindy :return-stream :rivulet stats/inv-dd-period)
                      (= fitness-type "score-x") (-> hystrindy :return-stream :rivulet stats/score-x)
                      )]
    (assoc hystrindy :fitness fitness)))

(defn get-hystrindies-fitnesses [hystrindies]
  (for [hystrindy hystrindies]
    (get-hystrindy-fitness hystrindy)))

(defn get-init-pop 
  ([ga-config] (get-init-pop ga-config nil))
  ([ga-config streams] (get-hystrindies-fitnesses (get-unique-hystrindies ga-config streams))))

(comment
  (def backtest-config (config/get-backtest-config-util
                        ["EUR_USD" "both"]
                        "ternary" 1 2 3 12 "H4"))

  (def streams (streams/fetch-formatted-streams backtest-config))

  (def strindy (strindy/make-strindy (backtest-config :strindy-config)))

  (def sieve-stream (strindy/get-sieve-stream strindy (streams :inception-streams)))

  (def return-stream (strindy/sieve->return sieve-stream (streams :intention-streams))))