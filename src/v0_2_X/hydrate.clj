(ns v0_2_X.hydrate
  (:require
   [v0_2_X.strindicator :as strindy]
   [v0_2_X.oanda_strindicator :as ostrindy]
   [v0_2_X.config :as config]))

(defn get-backtest-streams [backtest-config]
  (let [default-stream (vec (range (get backtest-config :num-data-points)))
        other-streams (ostrindy/get-instruments-streams backtest-config)
        streams (into [default-stream] other-streams)]
    {:id (.toString (java.util.UUID/randomUUID))
     :backtest-config (dissoc backtest-config :strindy-config)
     :time-stamp (quot (System/currentTimeMillis) 1000)
     :inception-streams (vec (for [ind (get-in backtest-config [:strindy-config :inception-ids])] (get streams ind)))
     :intention-streams (vec (for [ind (get-in backtest-config [:strindy-config :intention-ids])] (get streams ind)))}))

(defn hydrate-strindy [strindy streams]
  (let [sieve-stream (strindy/get-sieve-stream strindy (get streams :inception-streams))]
    {:id (.toString (java.util.UUID/randomUUID))
     :streams-id (get streams :id)
     :strindy strindy
     :sieve-stream sieve-stream
     :return-streams (strindy/get-return-streams-from-sieve sieve-stream (get streams :intention-streams))}))

(defn hydrate-strindies [strindies streams]
  (for [strindy strindies]
    (hydrate-strindy strindy streams)))

(defn is-sieve-unique? [test-stream sieve-streams]
  (not (some #(= % test-stream) sieve-streams)))

(defn get-hydrated-strindy [strindy-config streams]
  (let [strindy (strindy/make-strindy strindy-config)]
    (hydrate-strindy strindy streams)))

(defn get-unique-hystrindies
  ([ga-config streams] (get-unique-hystrindies ga-config streams (get-in ga-config [:pop-config :pop-size])))
  ([ga-config streams num-strindies]
   (loop [v []]
     (if (< (count v) num-strindies)
       (recur
        (let [new-hystrindy (get-hydrated-strindy (get-in ga-config [:backtest-config :strindy-config]) streams)
              new-sieve (get new-hystrindy :sieve-stream)
              prior-sieves (map :sieve-stream v)]
          (if (is-sieve-unique? new-sieve prior-sieves) (conj v new-hystrindy) v)))
       v))))

(defn get-hystrindies
  ([ga-config streams] (get-hystrindies ga-config streams (get-in ga-config [:pop-config :pop-size])))
  ([ga-config streams num-strindies]
   (loop [i 0 v (transient [])]
     (if (< i num-strindies)
       (recur (inc i)
              (conj! v (get-hydrated-strindy (get-in ga-config [:backtest-config :strindy-config]) streams)))
       (persistent! v)))))

(defn get-hystrindy-fitness [hystrindy]
  (let [fitness (-> hystrindy :return-streams first :sum-beck last)]
    (assoc hystrindy :fitness fitness)))

(defn get-hystrindies-fitnesses [hystrindies]
  (for [hystrindy hystrindies]
    (get-hystrindy-fitness hystrindy)))

(defn get-init-pop [ga-config streams]
  (get-hystrindies-fitnesses (get-unique-hystrindies ga-config streams)))


(comment
  (def backtest-config (config/get-backtest-config-util
                      ;; ["EUR_USD" "both" "AUD_USD" "inception" "GBP_USD" "inception" "USD_JPY" "inception"]
                        ["EUR_USD" "intention"]
                        "binary" 1 2 3 100 "M1"))

  (def streams (get-backtest-streams backtest-config))

  (def strindy (strindy/make-strindy-recur (backtest-config :strindy-config)))

  (def sieve-stream (strindy/get-sieve-stream strindy (streams :inception-streams)))

  (def return-streams (strindy/get-return-streams-from-sieve sieve-stream (streams :intention-streams)))
  )