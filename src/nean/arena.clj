(ns nean.arena
  (:require [nean.backtest :as backtest]
            [nean.trade :as trade]
            [constants :as constants]))

(defn run-and-save-backtest-and-procure-positions-sm []
  (let [backtest-params {:instruments ["EUR_USD"]
                         :granularity "H1"
                         :num-backtests-per-instrument 1
                         :xindy-config {:num-shifts 4
                                        :max-shift 20}
                         :pop-config {:pop-size 20
                                      :num-parents 5
                                      :num-children 15}
                         :ga-config {:num-generations 2
                                     :stream-count 200
                                     :back-pct 0.9}}
        backtest-id (backtest/run-and-save-backtest backtest-params)
        _ (println "backtest-id: " backtest-id)]
    (trade/procure-and-post-positions backtest-id)))

#_(run-and-save-backtest-and-procure-positions-sm)

;; we need to get a list of all tradeable instruments
;; for each instrument we need to get their target usd position value
;;    run backtest for instrument
;;    use backtest to get normalized score

;; we need a function that takes this list and updates position sizes on exchanges
;;    use instrument backtest scores to calculate target portfolio (list of {instrument : usd position size}s)
;;    for each target instrument position in target portfolio
;;        get instrument usd position size
;;        send update to exchange to change instrument position size
