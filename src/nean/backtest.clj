(ns nean.backtest
  (:require [api.oanda_api :as oa]
            [api.order_types :as ot]
            [clojure.core.async :as async]
            [config :as config]
            [env :as env]
            [file :as file]
            [nean.ga :as ga]
            [nean.xindy :as xindy]
            [stats :as stats]
            [util :as util]
            [buddy.core.hash :refer [md5]]
            [buddy.core.codecs :refer [bytes->hex]]))

(defn get-robustness [back-xindy fore-xindy]
  (stats/z-score (-> back-xindy :rivulet seq) (-> fore-xindy :rivulet seq)))

(defn combine-xindy [back-xindy fore-xindy]
  {:shifts (:shifts back-xindy)
   :robustness (get-robustness back-xindy fore-xindy)
   :back (dissoc back-xindy :shifts :rivulet)
   :fore (dissoc fore-xindy :shifts :rivulet)})

(defn combine-xindies [back-xindies fore-xindies]
  (map combine-xindy back-xindies fore-xindies))

(defn get-rindies [num-generations pop-config xindy-config back-stream fore-stream]
  (let [best-xindies (ga/get-parents (ga/run-generations num-generations pop-config xindy-config back-stream) pop-config)
        fore-xindies (for [xindy best-xindies]
                       (xindy/get-xindy-from-shifts (:shifts xindy) (:max-shift xindy-config) fore-stream))
        full-xindies (combine-xindies best-xindies fore-xindies)
        rindies (filter #(and (> (-> % :back :score) 0) (> (-> % :fore :score) 0) (> (:robustness %) -0.25)) full-xindies)]
    (println "num rindies:" (count rindies))
    rindies))

(defn generate-rifts [streams-map xindy-config pop-config ga-config]
  (let [rindies (get-rindies (:num-generations ga-config)
                             pop-config
                             xindy-config
                             (:back-stream streams-map)
                             (:fore-stream streams-map))
        rifts (mapv :shifts rindies)]
    rifts))

(defn generate-wrifts
  ([backtest-params] (generate-wrifts
                      (:instruments backtest-params)
                      (:xindy-config backtest-params)
                      (:pop-config backtest-params)
                      (:granularity backtest-params)
                      (:ga-config backtest-params)
                      (:num-backtests-per-instrument backtest-params)))
  ([instruments xindy-config pop-config granularity ga-config num-backtests-per-instrument]
   (vec
    (for [instrument instruments]
      (let [_ (println instrument)
            streams-map (xindy/get-back-fore-streams
                         instrument granularity
                         (:stream-count ga-config)
                         (:back-pct ga-config)
                         (:max-shift xindy-config))
            futures (for [_ (range num-backtests-per-instrument)]
                      (future (generate-rifts streams-map xindy-config pop-config ga-config)))
            rifts (vec (doall (mapcat deref futures)))]
        {:instrument instrument
         :rifts rifts
         :count (count rifts)})))))

(defn save-backtest
  ([wrifts xindy-config granularity filename]
   (let [file-content {:xindy-config xindy-config :granularity granularity :wrifts wrifts}]
     (file/write-file filename file-content)
     filename)))

(defn gen-backtest-id []
  (subs (bytes->hex (md5 (str (System/currentTimeMillis) (rand)))) 0 7))

(defn run-and-save-backtest
  ([] (run-and-save-backtest {:instruments ["BTCUSDT"]
                              :granularity "H1"
                              :num-backtests-per-instrument 1
                              :xindy-config {:num-shifts 4
                                             :max-shift 20}
                              :pop-config {:pop-size 20
                                           :num-parents 5
                                           :num-children 15}
                              :ga-config {:num-generations 2
                                          :stream-count 200
                                          :back-pct 0.9}}))
  ([backtest-params] (run-and-save-backtest
                      (:instruments backtest-params)
                      (:xindy-config backtest-params)
                      (:pop-config backtest-params)
                      (:granularity backtest-params)
                      (:ga-config backtest-params)
                      (:num-backtests-per-instrument backtest-params)))
  ([instruments xindy-config pop-config granularity ga-config num-backtests-per-instrument]
   (let [backtest-id (gen-backtest-id)
         filename (str "data/wrifts/" backtest-id ".edn")
         _ (file/write-file filename {:xindy-config {} :granularity "" :wrifts []})]
     (save-backtest
      (generate-wrifts instruments xindy-config pop-config granularity ga-config num-backtests-per-instrument)
      xindy-config
      granularity
      filename)
     backtest-id)))