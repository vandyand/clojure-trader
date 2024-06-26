(ns constants)

(defn backtest-config-util
  [instruments granularity num-backtests-per-instrument num-shifts max-shift pop-size parent-pct num-generations stream-count back-pct]
  {:instruments instruments
   :granularity granularity
   :num-backtests-per-instrument num-backtests-per-instrument
   :num-shifts num-shifts
   :max-shift max-shift
   :pop-size pop-size
   :parent-pct parent-pct
   :num-generations num-generations
   :stream-count stream-count
   :back-pct back-pct})

(def instruments
  ["AUD_CAD" "AUD_CHF" "AUD_JPY" "AUD_NZD" "AUD_SGD" "AUD_USD" "CAD_CHF" "CAD_JPY"
   "CAD_SGD" "CHF_JPY" "CHF_ZAR" "EUR_AUD" "EUR_CAD" "EUR_CHF" "EUR_CZK" "EUR_GBP"
   "EUR_JPY" "EUR_NZD" "EUR_SEK" "EUR_SGD" "EUR_USD" "EUR_ZAR" "GBP_AUD" "GBP_CAD"
   "GBP_CHF" "GBP_JPY" "GBP_NZD" "GBP_SGD" "GBP_USD" "GBP_ZAR" "NZD_CAD" "NZD_CHF"
   "NZD_JPY" "NZD_SGD" "NZD_USD" "SGD_CHF" "SGD_JPY" "USD_CAD" "USD_CHF" "USD_CNH"
   "USD_CZK" "USD_DKK" "USD_JPY" "USD_SEK" "USD_SGD" "USD_THB" "USD_ZAR" "ZAR_JPY"])

(comment
  (def currencies-by-liquidity
    ["USD" "EUR" "JPY" "GBP" "AUD" "CHF" "CAD" "NZD"])
  (def pairs-by-liquidity
    ["EUR_USD" "USD_JPY" "GBP_USD" "AUD_USD" "USD_CAD" "USD_CHF" "NZD_USD" "EUR_JPY" "GBP_JPY" "EUR_GBP" "AUD_JPY" "EUR_AUD"])
  )

(def granularities
  ["S5" "S10" "S15" "S30" "M1" "M2" "M4" "M5" "M10" "M15" "M30"
   "H1" "H2" "H3" "H4" "H6" "H8" "H12" "D" "W" "M"])

(defn get-range 
  ([min max] (get-range min max 1))
  ([min max step]
  (take-while #(<= % max) (iterate #(+ % step) min))))

#_(get-range 100 1000 100)

(def num-backtests-per-instrument
  (get-range 1 11))

(def num-shifts
  (get-range 2 40 2))

(def max-shift
  (get-range 100 1000 100))

(def pop-size
  (get-range 20 2000 100))

(def parent-pct
  (get-range 0.05 0.95 0.05))

(def num-generations
  (get-range 3 100 3))

(def stream-count
  (get-range 1000 20000 500))

(def back-pct
  (get-range 0.6 0.96 0.04))




