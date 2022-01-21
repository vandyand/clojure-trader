(ns ga
  (:require
   [clojure.pprint :as pp]
  ;;  [clojure.spec.alpha :as s]
  ;;  [clojure.spec.gen.alpha :as sgen]
  ;;  [clojure.test.check.generators :as gen]
   [clojure.string :as cs]
   [clojure.walk :as w]
   [clojure.zip :as z]
  ;;  [oz.core :as oz]
  ;;  [clojure.set :as set]
   [strategy :as strat]))




;; PLOT ALL THE STRATEGIES RETURN FUNCTIONS WITH THE INPUT DATA

(defn plot-strats [input-and-target-data strats]
  (apply strat/plot-strats input-and-target-data strats))

;; MAKE A BUNCH OF POPULATED STRATEGIES

(defn get-populated-strats [num-strats]
  (loop [i 0 v (transient [])]
    (if (< i num-strats)
      (recur (inc i) (conj! v (strat/get-populated-strat (str "strat-" i) input-and-target-data)))
      (persistent! v))))

(defn get-strat-fitness [strat]
  (let [fitness (last (strat :return-stream))]
    (assoc strat :fitness fitness)))

(defn get-best-strats [strats num]
  (take num (reverse (sort-by :fitness (map get-strat-fitness strats)))))


;; GET INPUT DATA (WITH TARGET AND TARGET DELTA)

(def input-and-target-data (strat/get-input-and-target-streams 4 10))

(def init-strats (get-populated-strats 8))

(def best-strats (get-best-strats init-strats 4))

(def tree (strat/make-tree))

;; TODO
;; Make new tree builder using nested vectors (easily zippable) (use zipper to build? doesn't really matter...)
;; Get tree solver and graphing working with vector trees.
;; Use zippers for modifying trees in GA