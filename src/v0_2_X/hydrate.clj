(ns v0_2_X.hydrate
  (:require [clojure.pprint :as pp]
            [v0_2_X.config :as config]
            [v0_2_X.strindicator :as strindy]
            [v0_2_X.oanda_strindicator :as ostrindy]))

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

(defn get-hydrated-strindy [strindy-config streams]
  (let [strindy (strindy/make-strindy-recur strindy-config)]
    (hydrate-strindy strindy streams)))

#_(def strindy (strindy/make-strindy-recur (get backtest-config :strindy-config)))
#_(def astrindy (strindy/ameliorate-strindy strindy))


#_(def streams (get-backtest-streams backtest-config))
#_(def hystrindy (hydrate-strindy strindy streams))