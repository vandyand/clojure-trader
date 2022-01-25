(ns vec_strategy
  (:require
   [strategy :as strat]
   [clojure.string :as cs]
   [clojure.zip :as z]
   [clojure.set :as set]
   [clojure.walk :as w]))

(def num-inputs 4)
(defn get-input-indxs
  "returns set of sets"
  [num-inputs]
  (set
   (filter
    #(not (nil? %))
    (for [x (range num-inputs) y (range num-inputs)]
      (when (not= x y)  #{x y})))))

(comment
  "
   1. Start at empty loc (root)
   2. Populate the empty loc with either
      a. boolean (different than sibling bool if applicable)
      b. index set (different than parent index sets)
   3. If cell is popoulated with index set, create two empty children
   4. If cell has an unpopulated child -> move to child
   5. Repeat step 2
   ")

(defn make-vec-tree
  "available-ind-sets is the set of total index sets minus (difference) node parent index sets
   depth-vec is a vector of [current-depth min-tree-depth max-tree-depth]. "
  [available-ind-sets depth-vec]
  (let [ind-set (rand-nth (seq available-ind-sets))
        new-available-ind-sets (set/difference available-ind-sets #{ind-set})]
    (let [make-child
          #(if
            (and
             (>= (first depth-vec) (nth depth-vec 1))
             (or (> (rand) 0.3) (empty? new-available-ind-sets) (>= (first depth-vec) (last depth-vec))))
             (rand-nth [true false])
             (make-vec-tree new-available-ind-sets (assoc depth-vec 0 (inc (first depth-vec)))))]
      (as-> [] $
        (z/vector-zip $)
        (z/append-child $ ind-set)
        (z/append-child $ (make-child))
        (z/append-child $ (make-child))
        (z/node $)))))

(defn print-tree [tree]
  (print (cs/replace (str tree) "[#{" "\n[#{"))
  tree)

(defn ameliorate-tree
  "Walk the tree. If two branches are identical, replace the node with the first branch"
  [tree]
  (w/postwalk
   #(if (and
         (= (type %) clojure.lang.PersistentVector)
         (= (nth % 1) (nth % 2)))
      (nth % 1)
      %)
   tree))

(defn make-tree
  ([] (make-tree num-inputs 4 6))
  ([num-inputs min-depth max-depth]
   (-> num-inputs
       (get-input-indxs)
       (make-vec-tree [0 min-depth max-depth])
       (ameliorate-tree))))

(defn solve-cond [inputs input-indxs]
  (> (inputs (first input-indxs)) (inputs (last input-indxs))))

(defn solve-tree
  "Solves tree for one 'moment in time'. inst-inputs (instance (or instant?) inputs) refers to the nth index of each input stream"
  [tree inst-inputs]
  (if (= (type tree) java.lang.Boolean)
    (if tree 1 0)
    (solve-tree
     (if (solve-cond inst-inputs (first tree))
       (nth tree 1)
       (nth tree 2))
     inst-inputs)))

(def input-and-target-streams (strat/get-input-and-target-streams num-inputs 100))

(defn get-populated-strat-from-tree
  [tree input-and-target-streams]
  (strat/get-populated-strat-from-tree tree input-and-target-streams solve-tree))

(defn get-populated-strat
  ([input-and-target-streams] (strat/get-populated-strat input-and-target-streams make-tree solve-tree)))

(time
 (do
   (def strat1 (get-populated-strat input-and-target-streams))
   (def strat2 (get-populated-strat input-and-target-streams))
   (def strat3 (get-populated-strat input-and-target-streams))
   (def strat4 (get-populated-strat input-and-target-streams))))
(strat/plot-strats input-and-target-streams strat1 strat2 strat3 strat4)