(ns v0_4_X.algo
  (:require
   [plot :as plot]
   [v0_2_X.streams :as streams]
   [v0_3_X.arena :as arena]
   [config :as config]
   [file :as file]
   [v0_2_X.hyst_factory :as factory]
   [clojure.core.async :as async]
   [util :as util]
   [v0_3_X.gauntlet :as gaunt]
   [helpers :as hlp]
   [env :as env]
   ))

(defn back-foretest-config [backtest-config]
  (assoc backtest-config :num-data-points (+ (backtest-config :shift-data-points) (backtest-config :num-data-points))
         :shift-data-points 0))

(defn get-robust-gahystrindy []
   (loop [result nil]
     (if result result
         (let [abcd (-> (rand) (* 190) (+ 160) int)
               foo (println "abcd: " abcd)
               num-data-points abcd
               shift-data-points abcd
               factory-config (apply config/get-factory-config-util
                                     [[["EUR_GBP" "both"]
                                       "ternary" 2 4 6 num-data-points shift-data-points "M1" "score-x"]
                                      [100 0.5 0.1 0.9]
                                      2 1])
               hyst (hlp/time-it "ALGO run factory^ " first (factory/run-factory factory-config))
               gaust (hlp/time-it "ALGO run-gauntlet single^ " gaunt/run-gauntlet-single hyst)
               zeroed-instrument (-> (back-foretest-config (-> gaust :backtest-config))
                                     streams/fetch-formatted-streams :intention-streams first plot/zero-instrument)
               plotter (when (env/get-env-data :GA_PLOTTING?) (plot/plot-streams [(-> gaust :g-beck) zeroed-instrument]))]
           (println "back-fitness: " (gaust :back-fitness))
           (println "fore-fitness: " (gaust :fore-fitness))
           (println "z-score: " (gaust :z-score))
           (println "g-score: " (gaust :g-score))
           (println "-------------------------------------------------")
           (recur (when (or (> (gaust :fore-fitness) (gaust :back-fitness)) (> (gaust :z-score) -0.25)) hyst))))))

(defn get-robust-gahys [number]
  (loop [gahys []]
    (if (>= (count gahys) number)
      gahys
      (do
        (println "num gahys so far:" (count gahys))
        (recur (conj gahys (get-robust-gahystrindy)))))))



(comment 

  (def robust-hysts (get-robust-gahys 10))

  ;; (arena/run-best-gaust [(-> gahy :hyst)])

  (let [schedule-chan (async/chan)
        future-times (util/get-future-unix-times-sec "M1")]

    (util/put-future-times schedule-chan future-times)

    (async/go-loop []
      (when-some [val (async/<! schedule-chan)]
        (arena/run-gausts robust-hysts))
      (when (not (env/get-env-data :KILL_GO_BLOCKS?)) (recur))))
  )


