(ns ga
  (:require
  ;;  [clojure.spec.alpha :as s]
  ;;  [clojure.spec.gen.alpha :as sgen]
  ;;  [clojure.test.check.generators :as gen]
  ;;  [clojure.string :as cs]
  ;;  [clojure.walk :as w]
  ;;  [oz.core :as oz]
  ;;  [clojure.set :as set]
   [strategy :as strat]))


;; GET INPUT DATA (WITH TARGET AND TARGET DELTA)

(def input-and-target-data (strat/get-input-and-target-streams 4 1000))


;; MAKE A BUNCH OF POPULATED STRATEGIES

(defn get-populated-strats [num-strats]
  (loop [i 0 v (transient [])]
    (if (< i num-strats)
      (recur (inc i) (conj! v (strat/get-populated-strat (str "strat-" i) input-and-target-data)))
      (persistent! v))))

(get-populated-strats 3)