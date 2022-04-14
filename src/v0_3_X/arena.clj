(ns v0_3_X.arena
  (:require
   [file :as file]
   [util :as util]
   [v0_2_X.config :as config]
   [v0_2_X.hydrate :as hyd]
   [v0_3_X.gauntlet :as gaunt]
   [v0_2_X.streams :as streams]
   [v0_1_X.oanda_api :as oa]))

(defn get-best-gausts
  ([gausts cutoff-score]
   (filterv (fn [gaust] (> (:g-score gaust) cutoff-score)) gausts)))

(defn get-best-gaust [gausts]
  (reduce (fn [acc cur] (if (> (:g-score cur) (:g-score acc)) cur acc)) gausts))

(defn get-intention-instruments [gaust]
  (map :name (filter #(not= (get % :incint) "inception") (-> gaust :streams-config))))

(defn run-arena []
  (let [gausts (gaunt/run-gauntlet)
        best-gaust (get-best-gaust gausts)
        intention-instruments (get-intention-instruments best-gaust)
        target-pos? (= 1 (-> best-gaust :g-sieve-stream last))]
    (doseq [instrument intention-instruments]
      (let [current-pos? (-> (oa/get-open-positions) :positions (util/find-in :instrument instrument))]
        (cond
          (and target-pos? (not current-pos?))
          (doall (oa/send-order-request instrument 100) (println instrument ": position opened!"))
          (and (not target-pos?) current-pos?)
          (doall (oa/send-order-request instrument (* -1 100)) (println instrument ": position closed!"))
          :else (println instrument ": nothing happened!"))))))

(comment
  (do
    (def gausts (gaunt/run-gauntlet))
    
    (println (map :g-score gausts))

    (def best-gaust (get-best-gaust gausts))

    (get-intention-instruments best-gaust)

    (let [intention-instruments (get-intention-instruments best-gaust)
          target-pos? (= 1 (-> best-gaust :g-sieve-stream last))]
      (doseq [instrument intention-instruments]
        (let [current-pos? (-> (oa/get-open-positions) :positions (util/find-in :instrument instrument))]
          (cond
            (and target-pos? (not current-pos?))
            (doall (oa/send-order-request instrument 100) (println instrument ": position opened!"))
            (and (not target-pos?) current-pos?)
            (doall (oa/send-order-request instrument (* -1 100)) (println instrument ": position closed!"))
            :else (println instrument ": nothing happened!"))))))
  )

(comment
  (oa/get-account-summary)
  (oa/get-open-positions)

  (oa/send-order-request "EUR_USD" 100)

  (oa/update-trade-with-id "186" "id-124")

  (oa/get-open-trade "182")

  (oa/get-open-trades)

  (oa/get-trade-client-id "182")

  (oa/get-trade-by-client-id "id-125"))


;; (comment
;;   (def gausts (file/get-hystrindies-from-file "gaustrindies.edn"))

;;   (def best-gausts (get-best-gausts gausts -0.2))
;;   (count best-gausts)

;;   (def best-gaust (get-best-gaust gausts))

;;   (do
;;     (def start-time (util/current-time-sec))
;;   ;; (def run-time-hrs (/ 0. 60.0))
;;   ;; (def run-time (long (* run-time-hrs 60 60)))
;;     (def run-time 4) ;; seconds
;;     (def end-time (+ start-time run-time))

;;     (def units 100)

;;     (while (< (util/current-time-sec) end-time)

;;       (def updated-gausts (update-gausts best-gausts))

;;       (doseq [updated-gaust updated-gausts]
;;         (let [intention-instruments (get-intention-instruments updated-gaust)
;;               target-pos? (= 1 (-> updated-gaust :g-sieve-stream last))
;;               current-pos? (> (-> (oa/get-open-positions) :positions count) 0)]
;;       ;; (println "target-pos?: " target-pos?)
;;       ;; (println "current-pos?: " current-pos?)
;;           (println "intention-instruments: " intention-instruments)
;;           (doseq [instrument intention-instruments]
;;         ;; (println instrument units)
;;             (cond
;;               (and target-pos? (not current-pos?))
;;               (doall (oa/send-order-request instrument units) (println "position opened!"))
;;               (and (not target-pos?) current-pos?)
;;               (doall (oa/send-order-request instrument (* -1 units)) (println "position closed!"))
;;               :else (println "nothing happened!")))))

;;       (Thread/sleep 1000))))

;; (do
;;   (def start-time (util/current-time-sec))
;;   (def run-time-hrs (/ 0.5 60.0))
;;   (def run-time (long (* run-time-hrs 60 60)))
;;   (def end-time (+ start-time run-time))

;;   (def units 100)

;;   (while (< (util/current-time-sec) end-time)

;;     (def updated-gausts (update-gaust best-gaust))

;;     (doseq [updated-gaust updated-gausts]
;;       (let [intention-instruments (get-intention-instruments updated-gaust)
;;             target-pos? (= 1 (-> updated-gaust :g-sieve-stream last))
;;             current-pos? (> (-> (oa/get-open-positions) :positions count) 0)]
;;         (println "target-pos?: " target-pos?)
;;         (println "current-pos?: " current-pos?)
;;         (run!
;;          (fn [instrument] (cond
;;                             (and target-pos? (not current-pos?))
;;                             (doall (oa/send-order-request instrument units) (println "position opened!"))
;;                             (and (not target-pos?) current-pos?)
;;                             (doall (oa/send-order-request instrument (* -1 units)) (println "position closed!"))
;;                             :else (println "nothing happened!")))
;;          intention-instruments)))
;;     (Thread/sleep 1000)))


