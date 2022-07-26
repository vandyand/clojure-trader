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
   [env :as env]
   [api.order_types :as ot]))

(defn get-intention-instruments-from-gaust [gaust]
  (map :name (filter #(not= (get % :incint) "inception") (-> gaust :backtest-config :streams-config))))

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
            pos-change (if current-pos-data (- target-pos current-pos) target-pos)
            order-options (ot/make-order-options-util instrument pos-change)]
        (println "best hyst ids: " (map :id hysts))
        (if (not= pos-change 0)
          (do (oa/send-order-request order-options)
              (println instrument ": position changed")
              (println "prev-pos: "  current-pos)
              (println "target-pos: " target-pos)
              (println "pos-change: " pos-change))
          (println "nothing happened"))))))

(defn post-gausts 
  [gausts]
  (let [intention-instruments (get-intention-instruments-from-gaust (first gausts))
        target-dirs (mapv #(-> % :fore-sieve-stream last) gausts)
        print-this (println (get-intention-instruments-from-gaust (first gausts)) " target directions:" target-dirs)
        account-balance (oa/get-account-balance)
        target-pos (if (> (count target-dirs) 0)
                     (int (* (/ account-balance 8) (stats/mean target-dirs)
                             (if (> (count target-dirs) 40) 40 (count target-dirs))))
                     0)]
    (doseq [instrument intention-instruments]
      (let [current-pos-data (-> (oa/get-open-positions) :positions (util/find-in :instrument instrument))
            long-pos (when current-pos-data (-> current-pos-data :long :units Integer/parseInt))
            short-pos (when current-pos-data (-> current-pos-data :short :units Integer/parseInt))
            current-pos (when current-pos-data (+ long-pos short-pos))
            units (if current-pos-data (- target-pos current-pos) target-pos)]
        (println "best gausts ids: " (map :id gausts))
        (println "best gausts z-score: " (map :z-score gausts))
        (println "best gausts back fitnesses: " (map :back-fitness gausts))
        (println "best gausts fore fitnesses: " (map :fore-fitness gausts))
        (if (not= units 0)
          (do (oa/send-order-request (ot/make-order-options-util instrument units))
              (println instrument ": position changed")
              (println "prev-pos: "  current-pos)
              (println "target-pos: " target-pos)
              (println "pos-change: " units))
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
      (let [dummy-gausts [(assoc (first gausts) :fore-sieve-stream [0] :id "DUMMY-GAUST--ZERO-POSITION")]]
       (post-gausts dummy-gausts))))))

(defn run-best-gausts-async
  [hysts-chan]
  (async/go-loop []
    (when-some [hysts (async/<! hysts-chan)]
      (let [gausts (gaunt/run-gauntlet hysts)
            best-gausts (gaunt/get-best-gausts gausts)]
        (if (> (count best-gausts) 0)
          (post-gausts best-gausts)
          (let [dummy-gausts [(assoc (first gausts) :fore-sieve-stream [0] :id "DUMMY-GAUST--ZERO-POSITION")]]
            (post-gausts dummy-gausts)))))
    (when (not (env/get-env-data :KILL_GO_BLOCKS?)) (recur))))

(defn run-arena 
  ([hysts-file-names] (run-arena hysts-file-names 0))
  ([hysts-file-names n]
  (when (< n (count hysts-file-names))
   (let [hysts-file-name (nth hysts-file-names n)]
    (run-best-gausts hysts-file-name)
    (run-arena hysts-file-names (inc n))
    ))))
