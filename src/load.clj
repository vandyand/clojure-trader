(ns load)

(load "/env")

(load "/api/headers")
(load "/api/util")
(load "/api/oanda_api")
(load "/api/binance_api")
;; (load "/api/order_types")
(load "/api/instruments")

(load "/v0_1_X/inputs")
(load "/v0_2_X/plot")
(load "/v0_1_X/strategy")
(load "/v0_1_X/ga")

(load "/util")

(load "/stats")

(load "/file")

(load "/config")

(load "/v0_2_X/strindicator")

(load "/v0_2_X/streams")

(load "/v0_2_X/hydrate")

(load "/v0_2_X/ga")

(load "/v0_2_X/hyst_factory")

(load "/v0_3_X/gauntlet")

(load "/v0_3_X/arena")

(load "/v0_3_X/runner")

(load "/v0_4_X/laboratory")


(comment
  (do
    (load "/v0_1_X/inputs")
    (load "/v0_2_X/plot"))

  (do
    (load "/v0_1_X/strategy")
    (load "/v0_1_X/oanda_api")
    (load "/v0_1_X/ga")

    (load "/util")

    (load "/v0_2_X/config")

    (load "/v0_2_X/strindicator")

    (load "/v0_2_X/streams")

    (load "/v0_2_X/hydrate")

    (load "/v0_2_X/ga")

    (load "/file")

    (load "/v0_2_X/hyst_factory")

    (load "/v0_3_X/gauntlet")

    (load "/v0_3_X/arena")

    (load "/v0_3_X/runner")))

