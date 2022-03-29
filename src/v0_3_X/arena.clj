(ns v0-3-X.arena
  (:require
   [file :as file]
   [v0_2_X.hydrate :as hyd]
   [v0_3_X.gauntlet :as gaunt]
   [v0_1_X.oanda_api :as oa]))

(defn get-best-ghysts
  ([ghysts cutoff-score]
   (filterv (fn [ghyst] (> (:g-score ghyst) cutoff-score)) ghysts)))

(defn get-best-ghyst [ghysts]
  (reduce (fn [acc cur] (if (> (:g-score cur) (:g-score acc)) cur acc)) ghysts))

(defn update-ghyst [ghyst]
  (let [back-streams (file/get-by-id "streams.edn" (get ghyst :streams-id))
        new-streams (hyd/get-backtest-streams (get back-streams :backtest-config))]
    (gaunt/run-gauntlet-single ghyst back-streams new-streams)))

(defn update-ghysts [ghysts]
  (for [ghyst ghysts]
    (update-ghyst ghyst)))


(def units 100)

(def ghysts (file/get-hystrindies-from-file "ghystrindies.edn"))
(def best-ghysts (get-best-ghysts ghysts 0.5))

(def start-time (quot (System/currentTimeMillis) 1000))
(def run-time-hrs 0.01)
(def run-time (* run-time-hrs 60 60))

(while (< (quot (System/currentTimeMillis) 1000) (+ start-time run-time))

  (def updated-ghysts (update-ghysts best-ghysts))
  
  (for [updated-ghyst updated-ghysts]
    (let [target-pos? (= 1 (-> updated-ghyst :g-sieve-stream last))
          current-pos? (> (-> (oa/get-open-positions) :positions count) 0)]
    (cond
      (and target-pos? (not current-pos?))
      (do (oa/send-order-request "EUR_USD" units) (println "position opened!"))
      (and (not target-pos?) current-pos?)
      (do (oa/send-order-request "EUR_USD" (* -1 units)) (println "position closed!"))
      :else (println "nothing happened!"))))
  (Thread/sleep 15000))


(oa/send-order-request "EUR_USD" 100)

(oa/update-trade-with-id "186" "id-124")

(oa/get-open-trade "182")

(oa/get-open-trades)

(oa/get-trade-client-id "182")

(oa/get-trade-by-client-id "id-125")
