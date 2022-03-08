(ns v0-2-X.populate
  (:require [clojure.pprint :as pp]
            [v0_2_X.config :as config]
            [v0_2_X.strindicator :as strindy]
            [v0_2_X.oanda_strindicator :as ostrindy]))

; Get config
(def config (config/get-config ["EUR_USD" "both"] "binary" 2 6 10 1000 "H1"))


; POPULATE! (not in GA way... put data in the config scaffolding as it were)

; Get strindy tree from strindy config
(def strindy (strindy/make-strindy-recur (get config :strindy-config)))
(pp/pprint strindy)

; Backtested Strindy: package of - strindy, sieve stream and return stream(s)

(def streams (ostrindy/get-instruments-stream (ostrindy/get-instruments-config config)))
(println streams)

(def sieve-stream (strindy/get-sieve-stream strindy streams))
(println sieve-stream)

(def return-streams (strindy/get-return-streams-from-strindy strindy (get config :strindy-config)))
(println return-streams)





; Arena strindy: package of - backtested strindy, arena-performance {returns, z-score, other-score?}
; Live practice strindy: arena strindy + live-practive-performance {returns, z-score, other-score?}
;; (skip one of arena strindy, live practice strindy? or combine them rather?)
; Live trading strindy: live practice strindy + live-trading-performance {returns, z-score, other-score?}
