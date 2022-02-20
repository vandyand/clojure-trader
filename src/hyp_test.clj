(ns hyp_test
  (:require
  ;;  [clojure.pprint :as pp]
  ;;  [clojure.spec.alpha :as s]
  ;;  [clojure.spec.gen.alpha :as sgen]
  ;;  [clojure.test.check.generators :as gen]
  ;;  [clojure.string :as cs]
  ;;  [clojure.walk :as w]
  ;;  [clojure.zip :as z]
  ;;  [oz.core :as oz]
  ;;  [clojure.set :as set]
   [v0_1_X.incubator.strategy :as strat]
   [v0_1_X.incubator.ga :as ga]
   [stats :as stats]))

(defn add-delta-return-stream-to-strat [strat]
  (assoc strat :return-stream-delta (strat/get-stream-delta (strat :return-stream) "return stream delta")))

(def best-strat (add-delta-return-stream-to-strat (first ga/best-strats)))

(def input-config (strat/get-input-config 4 20 1 0.1 0.1 100))

(def input-and-intention-streams-arena (strat/get-input-and-intention-streams input-config))

(def best-strat-arena (add-delta-return-stream-to-strat (strat/get-populated-strat (best-strat :tree) input-and-intention-streams-arena)))

(ga/plot-strats-with-input-intention-streams [best-strat best-strat-arena] input-and-intention-streams-arena)

(stats/z-score (best-strat :return-stream-delta) (best-strat-arena :return-stream-delta))

(let [arena-return-stream-delta (best-strat-arena :return-stream-delta)]
  (for [i (range  (count arena-return-stream-delta))]
    (let [partial-return-stream-delta (subvec arena-return-stream-delta 0 (+ 1 i))]
      (println
       (stats/z-score (best-strat :return-stream-delta) partial-return-stream-delta)))))

;; TODO
;; FINISH INCUBATOR
;; - USE TRADABLE INSTRUMENT(S) FOR TARGET DATA
;; - - GET TRADABLE INSTRUMENT HISTORICAL DATA (DAILY IS FINE FOR NOW)
;; - CREATE INDICATORS MANUALLY (SOME OF THE TRADITIONAL ONES I.E. MA, RSI, BB, ETC... THESE TAKE TRADABLE INSTRUMENTS AS INPUT)
;; - DESIGN ABSRACT INDICATOR GENERATOR
;; - BUILD INDICATOR GENERATOR
;; 
;; NICE TO HAVE
;; - SPEC EVERY FUNCTION
;; - FUZZ TEST EVERY FUNCTION WITH SPEC GENERATORS
;;
