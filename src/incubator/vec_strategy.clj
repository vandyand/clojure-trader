(ns incubator.vec_strategy
  (:require
   [strategy :as strat]
   [clojure.string :as cs]
   [clojure.zip :as z]
   [clojure.set :as set]
   [clojure.walk :as w]))

(defn get-index-pairs
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

(defn make-tree-recur
  "available-ind-sets is the set of total index sets minus (difference) node parent index sets"
  ([tree-config] (make-tree-recur (tree-config :index-pairs) tree-config 0))
  ([available-ind-sets tree-config depth]
   (let [ind-set (rand-nth (seq available-ind-sets))
         new-available-ind-sets (set/difference available-ind-sets #{ind-set})]
     (let [make-child
           #(if
             (and
              (>= depth (tree-config :min-depth))
              (or (> (rand) 0.3) (empty? new-available-ind-sets) (>= depth (tree-config :max-depth))))
              (rand-nth [true false])
              (make-tree-recur new-available-ind-sets tree-config (inc depth)))]
       (as-> [] $
         (z/vector-zip $)
         (z/append-child $ ind-set)
         (z/append-child $ (make-child))
         (z/append-child $ (make-child))
         (z/node $))))))

(defn print-tree [tree]
  (print (cs/replace (str tree) "[#{" "\n[#{"))
  tree)

(defn ameliorate-tree
  "This function only works on vector trees.
   Walk the tree. If two branches are identical, replace the node with the first branch"
  [tree]
  (w/postwalk
   #(if (and
         (= (type %) clojure.lang.PersistentVector)
         (= (nth % 1) (nth % 2)))
      (nth % 1)
      %)
   tree))

(defn make-tree
  ([tree-config]
   (-> tree-config
       (make-tree-recur)
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

(defn get-populated-strat-from-tree
  [tree input-and-target-streams]
  (strat/get-populated-strat-from-tree tree input-and-target-streams solve-tree))

(defn get-populated-strat
  ([input-and-target-streams tree-config] (strat/get-populated-strat input-and-target-streams tree-config make-tree solve-tree)))

(time
 (do
   (def input-config (strat/get-inputs-config 4 100 10 0.01 0 100))
   (def tree-config (strat/get-tree-config 2 6 (get-index-pairs (input-config :num-input-streams))))
   (def input-and-target-streams (strat/get-input-and-target-streams input-config))
   (def strat1 (get-populated-strat input-and-target-streams tree-config))
   (def strat2 (get-populated-strat input-and-target-streams tree-config))
   (def strat3 (get-populated-strat input-and-target-streams tree-config))
   (def strat4 (get-populated-strat input-and-target-streams tree-config))
   (strat/plot-strats-with-input-target-streams input-and-target-streams strat1 strat2 strat3 strat4)))