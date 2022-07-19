(ns v0_4_X.algo
  (:require
   [v0_2_X.plot :as plot]
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

(def gausts
 (time
  (loop [gaunts []]
  (if (>= (count gaunts) 2)
    gaunts
    
 (let [num-data-points 2000
       shift-data-points 2000
       factory-config (apply config/get-factory-config-util
                             [[["EUR_USD" "both" "AUD_USD" "inception" "GBP_USD" "inception"]
                               "ternary" 1 2 4 num-data-points shift-data-points "H2" "score-x"]
                              [20 0.4 0.1 0.5]
                              0 1])
       hyst (hlp/time-it "ALGO run factory^ " first (factory/run-factory factory-config))
       _gaunt (hlp/time-it "ALGO run-gauntlet single^ " gaunt/run-gauntlet-single hyst)]
   (println (count gaunts))
   (println "back-fitness: " (_gaunt :back-fitness))
   (println "fore-fitness: " (_gaunt :fore-fitness))
   (println "z-score: " (_gaunt :z-score))
   (println "g-score: " (_gaunt :g-score))
   (println "-------------------------------------------------")
   (recur (conj gaunts _gaunt)))))))

(defn back-fore-backtest-config [backtest-config]
  (assoc backtest-config :num-data-points (+ (backtest-config :shift-data-points) (backtest-config :num-data-points))
         :shift-data-points 0))

(def zeroed-instrument (-> (back-fore-backtest-config (-> gausts first :backtest-config)) 
                           streams/fetch-formatted-streams :intention-streams first plot/zero-instrument))

(plot/plot-streams [(-> gausts (nth 0) :g-beck) zeroed-instrument])

(defn get-gausts-means [gausts]
  {:m-b-fit (stats/mean (map :back-fitness gausts))
   :m-f-fit (stats/mean (map :fore-fitness gausts))
   :m-z-score (stats/mean (map :z-score gausts))
   :m-g-score (stats/mean (map :g-score gausts))})

(clojure.pprint/pprint (get-gausts-means gausts))


