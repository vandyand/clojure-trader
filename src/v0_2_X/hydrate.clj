(ns v0_2_X.hydrate
  (:require [clojure.pprint :as pp]
            [v0_2_X.config :as config]
            [v0_2_X.strindicator :as strindy]
            [v0_2_X.oanda_strindicator :as ostrindy]
            [v0_1_X.incubator.ga :as iga]
            [v0_1_X.incubator.strategy :as strat]))

; Get config
(def backtest-config (config/get-backtest-config-util
                      ["EUR_USD" "both" "AUD_USD" "inception" "GBP_USD" "inception" "USD_JPY" "inception"]
                      "binary" 2 4 10 12 "H1"))


; POPULATE! (not in GA way... put data in the config scaffolding as it were)

; Get strindy tree from strindy config

; Backtested Strindy: package of - strindy, sieve stream and return stream(s)

;; (def default-stream (vec (range (get backtest-config :num-data-points))))
;; (def other-streams (ostrindy/get-instruments-streams backtest-config))
;; (def streams (into [default-stream] other-streams))

;; (def inception-streams (vec (for [ind (get-in backtest-config [:strindy-config :inception-ids])] (get streams ind))))
;; (def intention-streams (vec (for [ind (get-in backtest-config [:strindy-config :intention-ids])] (get streams ind))))

;; (def sieve-stream (strindy/get-sieve-stream strindy inception-streams))

;; (def return-streams (strindy/get-return-streams-from-sieve sieve-stream intention-streams))


(defn get-backtest-streams [backtest-config]
  (let [default-stream (vec (range (get backtest-config :num-data-points)))
        other-streams (ostrindy/get-instruments-streams backtest-config)
        streams (into [default-stream] other-streams)]
    {:inception-streams (vec (for [ind (get-in backtest-config [:strindy-config :inception-ids])] (get streams ind)))
     :intention-streams (vec (for [ind (get-in backtest-config [:strindy-config :intention-ids])] (get streams ind)))}))

(defn hydrate-strindy [strindy streams]
  (let [sieve-stream (strindy/get-sieve-stream strindy (get streams :inception-streams))]
    {:strindy strindy
     :sieve-stream sieve-stream
     :return-streams (strindy/get-return-streams-from-sieve sieve-stream (get streams :intention-streams))}))

(defn hydrate-strindies [strindies streams]
  (for [strindy strindies]
    (hydrate-strindy strindy streams)))

(defn get-hydrated-strindy [strindy-config streams]
  (let [strindy (strindy/make-strindy strindy-config)]
    (hydrate-strindy strindy streams)))

#_(def strindy (strindy/make-strindy-recur (get backtest-config :strindy-config)))
#_(def astrindy (strindy/ameliorate-strindy strindy))


#_(def streams (get-backtest-streams backtest-config))
#_(def hystrindy (hydrate-strindy strindy streams))

(comment
  (def backtest-config (config/get-backtest-config-util
                        ["EUR_USD" "both" "AUD_USD" "inception" "GBP_USD" "inception" "USD_JPY" "inception"]
                        "binary" 1 3 4 12 "H1"))

  (def strindy (strindy/make-strindy (get backtest-config :strindy-config)))

; change branch function(s)
  (defn mutate-strindy
    ([strindy strindy-config] (mutate-strindy strindy strindy-config 100))
    ([strindy strindy-config max-num-mutations]
     (def a (atom 0))
     (w/postwalk
      (fn [form]
        (if (and (map? form)
                 (< (rand) 0.25)
                 (< @a max-num-mutations))
          (cond
            ; strat tree node
            (and (some #(= % :inputs) (keys form))
                 (some #(= % :tree) (keys (meta (form :fn)))))
            (let [mutated-tree (iga/get-mutated-tree ((meta (form :fn)) :tree))]
              (assoc form :fn (with-meta (fn [& args] (strat/solve-tree mutated-tree args)) {:name (str mutated-tree) :tree mutated-tree})))
            ; regular node
            (some #(= % :inputs) (keys form))
            (let [n (rand-int 6)]
              (cond
                (< n 3) (assoc form :fn (rand-nth strindy/strindy-funcs))
                (< n 4) (strindy/make-strindy
                         (config/get-strindy-config
                          "continuous" 1 2 3
                          (get strindy-config :inception-ids)
                          (get strindy-config :intention-ids)))
                (< n 5) (if (> (count (form :inputs)) 2)
                          (let [inputs (get form :inputs)]
                            (assoc form :inputs (subvec (shuffle inputs) 0 (dec (count inputs)))))
                          form)
                (< n 6) (assoc form :inputs (into (form :inputs) [(strindy/make-input (get strindy-config :inception-ids))]))))
            ; input node
            (some #(= % :id) (keys form))
            (if (> 0.5 (rand))
              (assoc form :id (rand-nth (get strindy-config :inception-ids)))
              (assoc form :shift (first (random-sample 0.5 (range)))))
            ; rand const node
            (some #(= % :fn) (keys form))
            (assoc form :fn (with-meta (constantly (rand)) {:name "rand const"}))
            :else form)
          form)) strindy)))

  (defn mutate-strindy-repeatedly
    ([strindy strindy-config num-repeats] (mutate-strindy-repeatedly strindy strindy-config num-repeats 0))
    ([strindy strindy-config num-repeats repeat-num]
     (strindy/print-strindy strindy)
     (let [new-strindy (mutate-strindy strindy strindy-config)]
       (if (>= repeat-num num-repeats)
         new-strindy
         (mutate-strindy-repeatedly new-strindy strindy-config num-repeats (inc repeat-num))))))

  (def mstrindy (mutate-strindy-repeatedly strindy (get backtest-config :strindy-config) 10))
  (println (= strindy mstrindy))
  (strindy/print-strindy strindy)
  (strindy/print-strindy mstrindy))
