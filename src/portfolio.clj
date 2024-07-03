
;; I have access to positions in binance and oanda
;; I have ability to run backtests on instruments to get "buy sell score" per instrument
;; I need current united states dollar position value on all my positions. 
;; I need to convert "buy sell scores" from each instrument into a "target portfolio" which is a list of all tradable (or "being traded" )instruments and the target usdollar value of said instrument
;; I need to update all positions to be equal to the target portfolio

(ns portfolio
  (:require [nean.arena :as arena]
            [nean.xindy :as xindy]
            [nean.trade :as trade]
            [api.oanda_api :as oanda_api]
            [clojure.set :as set]
            [clojure.core.async :as async]
            [constants :as constants]))

(defn fetch-current-positions []
  ;; Fetch positions from Binance and Oanda
  (let [binance-positions (oanda_api/get-binance-positions)
        oanda-positions (oanda_api/get-formatted-open-positions)]
    {:binance binance-positions
     :oanda oanda-positions}))

#_(fetch-current-positions)

(defn run-backtests [instruments]
  ;; Run backtests on instruments to get "buy sell scores"
  (let [backtest-params {:instruments instruments
                         :granularity "H1"
                         :num-backtests-per-instrument 7
                         :xindy-config {:num-shifts 70
                                        :max-shift 777}
                         :pop-config {:pop-size 77
                                      :num-parents 33
                                      :num-children 44}
                         :ga-config {:num-generations 7
                                     :stream-count 7777
                                     :back-pct 0.9}}]
    (arena/run-and-save-backtest backtest-params)))

(def backtest-id (run-backtests constants/pairs-by-liquidity))

(defn get-target-positions [backtest-arg]
  (let [backtest (if (string? backtest-arg)
                   (trade/backtest-id->backtest backtest-arg)
                   backtest-arg)
        _ (println "backtest" backtest)
        wrifts (:wrifts backtest)
        _ (println "wrifts" wrifts)
        things (for [wrift wrifts]
                 {:instrument (:instrument wrift)
                  :rel-buy-sell-score (let [vals (map #(get-in % [:total :last-rel-sieve-val]) (:rindies wrift))]
                                              (stats/mean vals))})]
    things))

(get-target-positions backtest-id)
