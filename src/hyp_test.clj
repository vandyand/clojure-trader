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
   [vec_strategy :as vat]
   [strategy :as strat]
   [ga :as ga]
   [stats :as stats]))

(defn add-delta-return-stream-to-strat [strat]
  (assoc strat :return-stream-delta (strat/get-stream-delta (strat :return-stream) "return stream delta")))

(def best-strat (add-delta-return-stream-to-strat (first ga/best-strats)))

(def input-and-target-streams-arena (strat/get-input-and-target-streams 4 20))

(def best-strat-arena (add-delta-return-stream-to-strat (vat/get-populated-strat-from-tree (best-strat :tree) input-and-target-streams-arena)))

(ga/plot-strats [best-strat best-strat-arena] input-and-target-streams-arena)


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
