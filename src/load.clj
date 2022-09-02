(ns load)

(load "/env")

(load "/api/headers")
(load "/api/util")
(load "/api/oanda_api")
(load "/api/binance_api")
(load "/api/order_types")
(load "/api/instruments")

(load "plot")
(load "/v0_1_X/inputs")
(load "/v0_1_X/strategy")
(load "/v0_1_X/ga")

(load "/util")

(load "/stats")

(load "/file")

(load "/config")

(load "/v0_2_X/solver")

(load "/v0_2_X/strindicator")

(load "/v0_2_X/streams")

(load "/v0_2_X/hystrindy")

(load "/v0_2_X/ga")

(load "/v0_2_X/hyst_factory")

(load "/v0_3_X/gauntlet")

(load "/v0_3_X/arena")

(load "/v0_3_X/runner")

(load "/v0_4_X/laboratory")

(load "/v0_4_X/algo")

(load "/nean/xindy2")
(load "/nean/ga")
(load "/nean/arena")

(load "/monitor/monitor")

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

