(ns v0_2_X.populate
  (:require [clojure.pprint :as pp]
            [v0_2_X.config :as config]
            [v0_2_X.strindicator :as strindy]
            [v0_2_X.oanda_strindicator :as ostrindy]))

; Get config
(def config (config/get-config ["EUR_USD" "both" "AUD_USD" "both"] "binary" 2 6 10 12 "H1"))


; POPULATE! (not in GA way... put data in the config scaffolding as it were)

; Get strindy tree from strindy config
(def strindy (strindy/make-strindy-recur (get config :strindy-config)))

; Backtested Strindy: package of - strindy, sieve stream and return stream(s)

(def instruments-config (ostrindy/get-instruments-config config))


(def default-stream (vec (range (get (first instruments-config) :count))))
(def other-streams (ostrindy/get-instruments-stream (rest instruments-config)))
(def streams (into [default-stream] other-streams))

(def inception-streams (vec (for [ind (get-in config [:strindy-config :inception-ids])] (get streams ind))))
(def intention-streams (vec (for [ind (get-in config [:strindy-config :intention-ids])] (get streams ind))))

(def sieve-stream (strindy/get-sieve-stream strindy inception-streams))

(def return-streams (strindy/get-return-streams-from-sieve sieve-stream intention-streams))


; Arena strindy: package of - backtested strindy, arena-performance {returns, z-score, other-score?}
; Live practice strindy: arena strindy + live-practive-performance {returns, z-score, other-score?}
;; (skip one of arena strindy, live practice strindy? or combine them rather?)
; Live trading strindy: live practice strindy + live-trading-performance {returns, z-score, other-score?}
