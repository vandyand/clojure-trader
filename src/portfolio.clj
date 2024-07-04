
;; I have access to positions in binance and oanda
;; I have ability to run backtests on instruments to get "buy sell score" per instrument
;; I need current united states dollar position value on all my positions. 
;; I need to convert "buy sell scores" from each instrument into a "target portfolio" which is a list of all tradable (or "being traded" )instruments and the target usdollar value of said instrument
;; I need to update all positions to be equal to the target portfolio

(ns portfolio
  (:require [nean.arena :as arena]
            [nean.xindy :as xindy]
            [api.oanda_api :as oanda_api]
            [clojure.set :as set]
            [clojure.core.async :as async]
            [constants :as constants]
            [stats :as stats]
            [clojure.pprint :as pprint]))

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

#_(def backtest-id (run-backtests constants/pairs-by-liquidity))

(defn get-instrument-scores [backtest-arg]
  (let [backtest (if (string? backtest-arg)
                   (arena/backtest-id->backtest backtest-arg)
                   backtest-arg)
        wrifts (:wrifts backtest)
        instrument-rel-scores (vec (for [wrift wrifts]
                                     {:instrument (:instrument wrift)
                                      :rel-buy-sell-score (let [vals (map #(get-in % [:total :last-rel-sieve-val]) (:rindies wrift))]
                                                            (stats/mean vals))
                                      :latest-price (oanda_api/get-latest-price (:instrument wrift))}))]
    instrument-rel-scores))

#_(def backtest-id "c34ef5b")

(defn instrument-ends-in-usd-or-usdt? [instrument]
  (let [suffix3 (subs instrument (max 0 (- (count instrument) 3)))
        suffix4 (subs instrument (max 0 (- (count instrument) 4)))]
    (or (= suffix3 "USD")
        (= suffix4 "USDT"))))

#_(instrument-ends-in-usd-or-usdt? "USD_JPY")
#_(instrument-ends-in-usd-or-usdt? "EUR_USD")
#_(instrument-ends-in-usd-or-usdt? "BTCUSDT")

(defn instrument-has-usd-in-it? [instrument]
  (not (nil? (re-find #"USD" instrument))))

#_(instrument-has-usd-in-it? "USD_JPY")
#_(instrument-has-usd-in-it? "EUR_JPY")
#_(instrument-has-usd-in-it? "EUR_USD")
#_(instrument-has-usd-in-it? "BTCUSDT")

(defn instrument-ends-in-jpy? [instrument]
  (= (subs instrument (max 0 (- (count instrument) 3))) "JPY"))

#_(instrument-ends-in-jpy? "USD_JPY")
#_(instrument-ends-in-jpy? "EUR_USD")

(defn instrument-ends-in-gbp? [instrument]
  (= (subs instrument (max 0 (- (count instrument) 3))) "GBP"))

#_(instrument-ends-in-gbp? "USD_JPY")
#_(instrument-ends-in-gbp? "EUR_GBP")

(defn get-target-position-amount [instrument latest-price usd-amount]
  (if (instrument-ends-in-usd-or-usdt? instrument)
    (/ usd-amount latest-price)
    (if (instrument-has-usd-in-it? instrument)
      (if (instrument-ends-in-jpy? instrument) 
        (* usd-amount latest-price 0.01)
        (* usd-amount latest-price))
      (if (instrument-ends-in-jpy? instrument) 
        (let [usd-jpy-latest-price (oanda_api/get-latest-price "USD_JPY")]
          (/ (* usd-amount latest-price) usd-jpy-latest-price))
        (if (instrument-ends-in-gbp? instrument)
          (let [gbp-usd-latest-price (oanda_api/get-latest-price "GBP_USD")]
            (* usd-amount latest-price gbp-usd-latest-price))
          (let [aud-usd-latest-price (oanda_api/get-latest-price "AUD_USD")]
            (* usd-amount latest-price aud-usd-latest-price)))))))

(defn is-negative-crypto? [instrument target-position]
  (and (util/is-crypto? instrument) (< target-position 0)))

(defn abs-sum [vs]
  (reduce + (pmap #(Math/abs %) vs)))

(defn get-target-scores [spend-amount instrument-scores]
  (let [rel-scores (mapv :rel-buy-sell-score instrument-scores) 
        sum-rel-scores (abs-sum rel-scores)
        scalar (/ spend-amount sum-rel-scores)
        usd-prices (for [instrament-score-record instrument-scores]
                     (let [usd-buy-sell-amount (* scalar (:rel-buy-sell-score instrament-score-record))]
                       (assoc instrament-score-record
                              :usd-buy-sell-amount usd-buy-sell-amount
                              :target-position (get-target-position-amount (:instrument instrament-score-record) (:latest-price instrament-score-record) usd-buy-sell-amount))))
        non-binance-sells (filterv #(not (is-negative-crypto? (:instrument %) (:target-position %))) usd-prices)]
    non-binance-sells))

#_(def forex-target-positions (filter #(util/is-forex? (:instrument %)) target-positions))

(defn get-balanced-scores [target-scores]
  (for [tsc target-scores]
    (if (util/is-forex? (:instrument tsc))
      (assoc tsc :target-position-original (:target-position tsc) :target-position (* 25 (:target-position tsc)))
      tsc)))

#_(def backtest-id "c34ef5b")

#_(def inscs (get-instrument-scores backtest-id))
#_(def bscs (get-balanced-scores inscs))

#_(let [x 480
        y "c34ef5b"
        inscs (get-instrument-scores y)
        tscs (get-target-scores 480 inscs)
        bscs (get-balanced-scores tscs)]
    bscs)

(defn shoot-money-x-from-backtest-y [x y]
  (let [inscs (get-instrument-scores y)
         tscs (get-target-scores x inscs)
         bscs (get-balanced-scores tscs)] 
    (arena/post-target-positions bscs)))

(shoot-money-x-from-backtest-y 240 "c34ef5b")
