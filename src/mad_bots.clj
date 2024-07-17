(ns mad-bots
  (:require [constants :as constants]
            [nean.xindy :as xindy]
            [stats :as stats]
            [nean.arena :as arena]))

;; input all instruments historic candlebar data
(def bot-config {:instruments constants/pairs-by-liquidity
                 :granularity "H1"
                 :backtest-config
                 {:arg1 1
                  :arg2 2}})

(def instruments-data
  (vec
   (pmap (fn [instrument]
           {:instrument (keyword instrument)
            :data (xindy/get-stream instrument (:granularity bot-config) 1200)
            :rel-buy-sell-score 0.0})
         (:instruments bot-config))))

(doseq [instrument instruments-data]
  (println (:instrument instrument) (count (:data instrument))))

(first instruments-data)


(defn simple-strat [instrument-record]
  (let [last-val (last (:data instrument-record))
        mean-data (stats/mean (:data instrument-record))
        stddev-data (stats/stdev (:data instrument-record))
        rel-score (* -1 (/ (- last-val mean-data) mean-data stddev-data))]
    (assoc instrument-record :rel-buy-sell-score rel-score)))

(defn algorithm [instruments-data]
  (mapv simple-strat instruments-data))

(defn format-instruments-data [instruments-data]
  (mapv :data instruments-data))

#_(format-instruments-data instruments-data)


(def target-instruments-data (algorithm instruments-data))

(doseq [instrument target-instruments-data]
  (println (:instrument instrument) (:rel-buy-sell-score instrument)))


(defn post-demo-target-pos [instrument target-pos]
  true)

(defn post-demo-target-positions [target-instrument-positions]
  (doseq [target-instrument-position target-instrument-positions]
    (post-demo-target-pos (:instrument target-instrument-position)
                          (:target-position target-instrument-position))))


;; output relative buy sell scores


