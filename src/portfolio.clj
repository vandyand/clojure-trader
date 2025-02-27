(ns portfolio
  (:require [nean.arena :as arena]
            [api.oanda_api :as oanda_api]
            [stats :as stats]
            [constants :as constants]))

(def instrument-scores-cache (atom {}))

(defn get-instrument-scores [backtest-arg]
  (let [cache-key backtest-arg
        current-time (System/currentTimeMillis)
        cached-data (get @instrument-scores-cache cache-key)
        cache-valid? (and cached-data (< (- current-time (:timestamp cached-data)) (* 60 60 1000)))]
    (if cache-valid?
      (:data cached-data)
      (let [backtest (if (string? backtest-arg)
                       (arena/backtest-id->backtest backtest-arg)
                       backtest-arg)
            wrifts (:wrifts backtest)
            instrument-rel-scores (vec (for [wrift wrifts]
                                         {:instrument (:instrument wrift)
                                          :rel-buy-sell-score (let [vals (map #(get-in % [:total :last-rel-sieve-val]) (:rindies wrift))]
                                                                (stats/mean vals))
                                          :latest-price (oanda_api/get-latest-price (:instrument wrift))}))]
        (swap! instrument-scores-cache assoc cache-key {:data instrument-rel-scores :timestamp current-time})
        instrument-rel-scores))))

#_(get-instrument-scores backtest-id)


(defn instrument-ends-in-usd-or-usdt? [instrument]
  (let [suffix3 (subs instrument (max 0 (- (count instrument) 3)))
        suffix4 (subs instrument (max 0 (- (count instrument) 4)))]
    (or (= suffix3 "USD")
        (= suffix4 "USDT"))))

(defn instrument-has-usd-in-it? [instrument]
  (not (nil? (re-find #"USD" instrument))))

(defn instrument-ends-in-jpy? [instrument]
  (= (subs instrument (max 0 (- (count instrument) 3))) "JPY"))

(defn instrument-ends-in-gbp? [instrument]
  (= (subs instrument (max 0 (- (count instrument) 3))) "GBP"))

(defn instrument-ends-in-nzd? [instrument]
  (= (subs instrument (max 0 (- (count instrument) 3))) "NZD"))

(defn instrument-ends-in-aud? [instrument]
  (= (subs instrument (max 0 (- (count instrument) 3))) "AUD"))

(defn instrument-ends-in-cad? [instrument]
  (= (subs instrument (max 0 (- (count instrument) 3))) "CAD"))

(defn instrument-ends-in-chf? [instrument]
  (= (subs instrument (max 0 (- (count instrument) 3))) "CHF"))

(defn get-target-position-amount [instrument latest-price usd-amount]
  (cond
    (instrument-ends-in-usd-or-usdt? instrument) (/ usd-amount latest-price)
    (instrument-has-usd-in-it? instrument) (cond
                                             (instrument-ends-in-jpy? instrument) (* usd-amount latest-price 0.01)
                                             :else (* usd-amount latest-price))
    (instrument-ends-in-jpy? instrument) (/ (* usd-amount latest-price) (oanda_api/get-latest-price "USD_JPY"))
    (instrument-ends-in-cad? instrument) (/ (* usd-amount latest-price) (oanda_api/get-latest-price "USD_CAD"))
    (instrument-ends-in-chf? instrument) (/ (* usd-amount latest-price) (oanda_api/get-latest-price "USD_CHF"))
    (instrument-ends-in-gbp? instrument) (* usd-amount latest-price (oanda_api/get-latest-price "GBP_USD"))
    (instrument-ends-in-nzd? instrument) (* usd-amount latest-price (oanda_api/get-latest-price "NZD_USD"))
    (instrument-ends-in-aud? instrument) (* usd-amount latest-price (oanda_api/get-latest-price "AUD_USD"))
    :else (/ usd-amount latest-price)))

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
        updated-usd-prices (mapv (fn [record]
                                   (if (is-negative-crypto? (:instrument record) (:target-position record))
                                     (assoc record :target-position 0.0)
                                     record))
                                 usd-prices)]
    updated-usd-prices))

#_(def forex-target-positions (filter #(util/is-forex? (:instrument %)) target-positions))

(defn get-balanced-scores [target-scores]
  (for [tsc target-scores]
    (if (util/is-forex? (:instrument tsc))
      (assoc tsc :target-position-original (:target-position tsc) :target-position (* 25 (:target-position tsc)))
      tsc)))

#_(let [x 480
        y backtest-id
        inscs (get-instrument-scores y)
        _ (println "inscs" inscs)
        tscs (get-target-scores 480 inscs)
        _ (println "tscs" tscs)
        bscs (get-balanced-scores tscs)]
    bscs)

(defn shoot-money-x-from-backtest-y [x y]
  (let [inscs (get-instrument-scores y)
        tscs (get-target-scores x inscs)
        bscs (get-balanced-scores tscs)]
    (arena/post-target-positions bscs)))

(defn run-backtest [instruments]
  ;; Run backtests on instruments to get "buy sell scores"
  (let [backtest-params {:instruments instruments
                         :granularity "H1"
                         :num-backtests-per-instrument 7
                         :xindy-config {:num-shifts 14
                                        :max-shift 777}
                         :pop-config {:pop-size 77
                                      :num-parents 44
                                      :num-children 33}
                         :ga-config {:num-generations 7
                                     :stream-count 7777
                                     :back-pct 0.77}}]
    (arena/run-and-save-backtest backtest-params)))

#_(shoot-money-x-from-backtest-y 100 (run-backtest constants/pairs-by-liquidity-oanda))
#_(shoot-money-x-from-backtest-y 100 (run-backtest constants/pairs-by-liquidity-crypto))
(shoot-money-x-from-backtest-y 120 (run-backtest constants/pairs-by-liquidity))

(defn get-accounts-worth []
  (let [oanda-nav (oanda_api/get-account-nav)
        binance-nav (oanda_api/get-binance-account-usd-amount)
        total-nav (+ oanda-nav binance-nav)
        ret {:oanda oanda-nav
             :binance binance-nav
             :total total-nav
             :timestamp (System/currentTimeMillis)}]
    (println ret)
    ret))

#_(get-accounts-worth)

#_(oanda_api/get-account-nav)

#_(oanda_api/get-binance-account-usd-amount)
