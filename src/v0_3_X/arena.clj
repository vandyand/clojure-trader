(ns v0_3_X.arena
  (:require
   [file :as file]
   [util :as util]
   [helpers :as hlp]
   [config :as config]
   [v0_2_X.hydrate :as hyd]
   [v0_3_X.gauntlet :as gaunt]
   [v0_2_X.streams :as streams]
   [api.oanda_api :as oa]
   [stats :as stats]
   [clojure.core.async :as async]
   [env :as env]))

(defn get-intention-instruments-from-gaust [gaust]
  (map :name (filter #(not= (get % :incint) "inception") (-> gaust :streams-config))))

(defn get-intention-instruments-from-hyst [hyst]
  (map :name (filter #(not= (get % :incint) "inception") (-> hyst :backtest-config :streams-config))))

(defn get-robustness [hysts-file-name]
  (let [gausts (gaunt/run-gauntlet hysts-file-name)
        best-gausts (gaunt/get-best-gausts gausts)]
    (println "num gausts: " (count gausts))
    (println "num best gausts: " (count best-gausts))
  (double (/ (-> best-gausts count) (count gausts)))))

(defn get-robustness-async [hysts-chan]
  (async/go-loop []
    (when-some [hysts (async/<! hysts-chan)]
      (let [gausts (gaunt/run-gauntlet hysts)
            best-gausts (gaunt/get-best-gausts gausts)]
        (println "num gausts: " (count gausts))
        (println "num best gausts: " (count best-gausts))
        (println (double (/ (-> best-gausts count) (count gausts))))))
    (when (not (env/get-env-data :KILL_GO_BLOCKS?)) (recur))))

(defn post-hysts [hysts]
  (let [intention-instruments (get-intention-instruments-from-hyst (first hysts))
        target-dirs (mapv #(-> % :sieve-stream last) hysts)
        foo (println intention-instruments " target directions:" target-dirs)
        target-pos (if (> (count target-dirs) 0)
                     (int (* 100 
                             (if (> (count target-dirs) 10) 10 (count target-dirs)) 
                             (stats/mean target-dirs)))
                     0)]
    (doseq [instrument intention-instruments]
      (let [current-pos-data (-> (oa/get-open-positions) :positions (util/find-in :instrument instrument))
            long-pos (when current-pos-data (-> current-pos-data :long :units Integer/parseInt))
            short-pos (when current-pos-data (-> current-pos-data :short :units Integer/parseInt))
            current-pos (when current-pos-data (+ long-pos short-pos))
            pos-change (if current-pos-data (- target-pos current-pos) target-pos)]
        (println "best hyst ids: " (map :id hysts))
        (if (not= pos-change 0)
          (do (oa/send-order-request instrument pos-change)
              (println instrument ": position changed")
              (println "prev-pos: "  current-pos)
              (println "target-pos: " target-pos)
              (println "pos-change: " pos-change))
          (println "nothing happened"))))))

(defn post-gausts [gausts]
  (let [intention-instruments (get-intention-instruments-from-gaust (first gausts))
        target-dirs (mapv #(-> % :g-sieve-stream last) gausts)
        foo (println (get-intention-instruments-from-gaust (first gausts)) " target directions:" target-dirs)
        target-pos (if (> (count target-dirs) 0)
                     (int (* 250 (stats/mean target-dirs)
                             (if (> (count target-dirs) 40) 40 (count target-dirs)) 
                             ))
                     0)]
    (doseq [instrument intention-instruments]
      (let [current-pos-data (-> (oa/get-open-positions) :positions (util/find-in :instrument instrument))
            long-pos (when current-pos-data (-> current-pos-data :long :units Integer/parseInt))
            short-pos (when current-pos-data (-> current-pos-data :short :units Integer/parseInt))
            current-pos (when current-pos-data (+ long-pos short-pos))
            pos-change (if current-pos-data (- target-pos current-pos) target-pos)]
        (println "best gausts ids: " (map :id gausts))
        (println "best gausts z-score: " (map :z-score gausts))
        (println "best gausts back fitnesses: " (map :back-fitness gausts))
        (println "best gausts fore fitnesses: " (map :fore-fitness gausts))
        (if (not= pos-change 0)
          (do (oa/send-order-request instrument pos-change)
              (println instrument ": position changed")
              (println "prev-pos: "  current-pos)
              (println "target-pos: " target-pos)
              (println "pos-change: " pos-change))
          (println "nothing happened"))))))

(defn run-best-gaust 
  ([] (run-best-gaust "hystrindies.edn"))
  ([hysts-file-name]
  (let [gausts (gaunt/run-gauntlet hysts-file-name)
        best-gaust (gaunt/get-best-gaust gausts)]
      (post-gausts best-gaust))))

(defn run-best-gausts 
  ([] (run-best-gausts "hystrindies.edn"))
  ([hysts-file-name]
  (let [gausts (gaunt/run-gauntlet hysts-file-name)
        ;; bar (println gausts)
        best-gausts (gaunt/get-best-gausts gausts)]
    (if (> (count best-gausts) 0)
      (post-gausts best-gausts)
      (let [dummy-gausts [(assoc (first gausts) :g-sieve-stream [0] :id "DUMMY-GAUST--ZERO-POSITION")]]
       (post-gausts dummy-gausts))))))

(defn run-best-gausts-async
  ([hysts-chan]
  (async/go-loop []
    (when-some [hysts (async/<! hysts-chan)]
      (let [gausts (gaunt/run-gauntlet hysts)
        ;; bar (println gausts)
            best-gausts (gaunt/get-best-gausts gausts)]
        (if (> (count best-gausts) 0)
          (post-gausts best-gausts)
          (let [dummy-gausts [(assoc (first gausts) :g-sieve-stream [0] :id "DUMMY-GAUST--ZERO-POSITION")]]
            (post-gausts dummy-gausts)))))
    (when (not (env/get-env-data :KILL_GO_BLOCKS?)) (recur)))))

(defn run-arena 
  ([hysts-file-names] (run-arena hysts-file-names 0))
  ([hysts-file-names n]
  (when (< n (count hysts-file-names))
   (let [hysts-file-name (nth hysts-file-names n)]
    (run-best-gausts hysts-file-name)
    (run-arena hysts-file-names (inc n))
    ))))

(comment
  ;; (do
    (def gausts (gaunt/run-gauntlet "M15-200-#EUR_USD.edn"))
    
    (println (map :g-score gausts))

    (def best-gaust (gaunt/get-best-gaust gausts))

    (get-intention-instruments-from-gaust best-gaust)

    (let [intention-instruments (get-intention-instruments-from-gaust best-gaust)
          target-pos? (= 1 (-> best-gaust :g-sieve-stream last))]
      (doseq [instrument intention-instruments]
        (let [current-pos? (-> (oa/get-open-positions) :positions (util/find-in :instrument instrument))]
          (cond
            (and target-pos? (not current-pos?))
            (doall (oa/send-order-request instrument 100) (println instrument ": position opened!"))
            (and (not target-pos?) current-pos?)
            (doall (oa/send-order-request instrument (* -1 100)) (println instrument ": position closed!"))
            :else (println instrument ": nothing happened!"))))))
  ;; )

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
;;         (let [intention-instruments (get-intention-instruments-from-gaust updated-gaust)
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
;;       (let [intention-instruments (get-intention-instruments-from-gaust updated-gaust)
;;             target-pos? (= 1 (-> updated-gaust :g-sieve-stream last))
;;             current-pos? (> (-> (oa/get-open-positions) :positions count) 0)]
;;         (println "target-pos?: " target-pos?)
;;         (println "current-pos?: " current-pos?)
;;         (run!
;;          (fn [instrument] (cond
;;                             (and target-pos? (not current-pos?))
;;                             (doall (oa/send-order-request instrument units) (println "position opened!"))
;;                             (and (not target-pos?) current-pos?)
;;                             (doall (oa/send-order-request instrument (* -1 units)) (` "position closed!"))
;;                             :else (println "nothing happened!")))
;;          intention-instruments)))
;;     (Thread/sleep 1000)))


