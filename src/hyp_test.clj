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
  ;;  [vec_strategy :as vat]
  ;;  [strategy :as strat]
   [ga :as ga]
   [stats :as stats]))

;; USE INPUT AND TARGET DATA FROM VAT
(def best-strat )




;; TODO
;; MAKE P-TEST FUNCTION ✅
;; MAKE SOME EXTENDED INPUT DATA
;; GET BEST STRATEGY(IES) FROM GA
;; GET PERFORMANCE ON OUT OF SAMPLE DATA
;; GET P-TEST VALUE OF PERFORMANCE ON OUT OF SAMPLE DATA
;; CODIFY THIS AND APPLY AT EVERY TIME STEP OF OOS DATA. STOP STRAT WHEN P-VALUE DIPS TO SOME YET-TO-BE-DETERMINED VALUE
;; 
;; START WORKING WITH LIVE DATA
;;     MAKE INDICATOR GENERATOR FUNCTION?
;; 
;; NICE TO HAVE
;;     SPEC EVERY FUNCTION
;;     FUZZ TEST EVERY FUNCTION WITH SPEC GENERATORS