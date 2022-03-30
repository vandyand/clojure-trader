(ns v0-3-X.arena
  (:require
   [file :as file]
   [v0_2_X.hydrate :as hyd]
   [v0_3_X.gauntlet :as gaunt]
   [v0_1_X.oanda_api :as oa]))

(defn get-best-gausts
  ([gausts cutoff-score]
   (filterv (fn [gaust] (> (:g-score gaust) cutoff-score)) gausts)))

(defn get-best-gaust [gausts]
  (reduce (fn [acc cur] (if (> (:g-score cur) (:g-score acc)) cur acc)) gausts))

(defn update-gaust [gaust]
  (let [back-streams (file/get-by-id "streams.edn" (get gaust :streams-id))
        new-streams (hyd/get-backtest-streams (get back-streams :backtest-config))]
    (gaunt/run-gauntlet-single gaust back-streams new-streams)))

(defn update-gausts [gausts]
  (for [gaust gausts]
    (update-gaust gaust)))


(def units 100)

(def gausts (file/get-hystrindies-from-file "gaustrindies.edn"))
(def best-gausts (get-best-gausts gausts -0.2))

;; (for [gaust best-gausts])

(def start-time (quot (System/currentTimeMillis) 1000))
(def run-time-hrs (/ 0.5 60.0))
(def run-time (long (* run-time-hrs 60 60)))
(def end-time (+ start-time run-time))

(def updated-gausts (update-gausts best-gausts))


(while (< (quot (System/currentTimeMillis) 1000) end-time)

  (println "this ran")
  (def updated-gausts (update-gausts best-gausts))
  (println (count updated-gausts))


  (for [updated-gaust updated-gausts]
    (let [foo (println (keys updated-gaust))
          target-pos? (= 1 (-> updated-gaust :g-sieve-stream last))
          current-pos? (> (-> (oa/get-open-positions) :positions count) 0)]
      (cond
        (and target-pos? (not current-pos?))
        (do (oa/send-order-request "EUR_USD" units) (println "position opened!"))
        (and (not target-pos?) current-pos?)
        (do (oa/send-order-request "EUR_USD" (* -1 units)) (println "position closed!"))
        :else (println "nothing happened!"))))

  (Thread/sleep 1000))


(oa/send-order-request "EUR_USD" 100)

(oa/update-trade-with-id "186" "id-124")

(oa/get-open-trade "182")

(oa/get-open-trades)

(oa/get-trade-client-id "182")

(oa/get-trade-by-client-id "id-125")
