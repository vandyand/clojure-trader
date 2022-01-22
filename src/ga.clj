(ns ga
  (:require
  ;;  [clojure.pprint :as pp]
  ;;  [clojure.spec.alpha :as s]
  ;;  [clojure.spec.gen.alpha :as sgen]
  ;;  [clojure.test.check.generators :as gen]
  ;;  [clojure.string :as cs]
  ;;  [clojure.walk :as w]
   [clojure.zip :as z]
  ;;  [oz.core :as oz]
  ;;  [clojure.set :as set]
   [vec-strategy :as vat]
   [strategy :as strat]))




;; PLOT ALL THE STRATEGIES RETURN FUNCTIONS WITH THE INPUT DATA

(defn plot-strats [input-and-target-data strats]
  (apply strat/plot-strats input-and-target-data strats))

;; MAKE A BUNCH OF POPULATED STRATEGIES

(defn get-populated-strats [num-strats input-and-target-data]
  (loop [i 0 v (transient [])]
    (if (< i num-strats)
      (recur (inc i) (conj! v (vat/get-populated-strat input-and-target-data)))
      (persistent! v))))

(defn get-strat-fitness [strat]
  (let [fitness (last (strat :return-stream))]
    (assoc strat :fitness fitness)))

(defn get-best-strats [strats num]
  (take num (reverse (sort-by :fitness (map get-strat-fitness strats)))))


;; MUTATE ZIPPERS FUNCTIONS
(defn rand-bool []
  (> 0.5 (rand)))

(defn branchA [loc]
  (if (z/branch? loc) (-> loc (z/down) (z/right)) loc))
(defn branchB [loc]
  (if (z/branch? loc) (-> loc (z/down) (z/rightmost)) loc))
(defn rand-branch [loc]
  (if
   (z/branch? loc)
    (if
     (rand-bool)
      (branchA loc)
      (branchB loc))
    loc))

(defn prune-branchA [loc]
  (if (z/branch? loc) (-> loc (z/replace (-> loc (branchB) (z/node)))) loc))
(defn prune-branchB [loc]
  (if (z/branch? loc) (-> loc (z/replace (-> loc (branchA) (z/node)))) loc))
(defn prune-rand-branch [loc]
  (if (z/branch? loc) (-> loc (z/replace (-> loc (rand-branch) (z/node)))) loc))

;; (defn replace-branchA-with-true [loc]
;;   (if (z/branch? loc) (-> loc (branchA) (z/replace true) (z/up)) loc))
;; (defn replace-branchA-with-false [loc]
;;   (if (z/branch? loc) (-> loc (branchA) (z/replace false) (z/up)) loc))
;; (defn replace-branchB-with-true [loc]
;;   (if (z/branch? loc) (-> loc (branchB) (z/replace true) (z/up)) loc))
;; (defn replace-branchB-with-false [loc]
;;   (if (z/branch? loc) (-> loc (branchB) (z/replace false) (z/up)) loc))
(defn replace-rand-branch-with-rand-bool [loc]
  (if (z/branch? loc) (-> loc (rand-branch) (z/replace (rand-bool)) (z/up)) loc))


(defn make-new-tree-branch [num-inputs]
  (vat/make-vec-tree (vat/get-input-indxs num-inputs) [0 0 1]))

;; (defn expand-branchA [loc]
;;   (if (and (z/branch? loc) (not (z/branch? (branchA loc))))
;;     (let [new-node (make-new-tree-branch 4)] (-> loc (branchA) (z/replace new-node) (z/up))) loc))
;; (defn expand-branchB [loc]
;;   (if (and (z/branch? loc) (not (z/branch? (branchB loc))))
;;     (let [new-node (make-new-tree-branch 4)] (-> loc (branchB) (z/replace new-node) (z/up))) loc))

;; (defn new-branchA [loc]
;;   (when (z/branch? loc)
;;     (let [new-node (make-new-tree-branch 4)] (-> loc (branchA) (z/replace new-node) (z/up)))))
;; (defn new-branchB [loc]
;;   (when (z/branch? loc)
;;     (let [new-node (make-new-tree-branch 4)] (-> loc (branchB) (z/replace new-node) (z/up)))))
(defn new-rand-branch [loc]
  (when (z/branch? loc)
    (let [new-node (make-new-tree-branch 4)] (-> loc (rand-branch) (z/replace new-node) (z/up)))))

(defn switch-branches [loc]
  (when (z/branch? loc) (-> loc (z/append-child (-> loc (branchA) (z/node))) (branchA) (z/remove) (z/up))))

(defn rand-bottom-loc
  "recursively dives a tree until it finds a bool, then returns it's parent node"
  [loc] (if (not (z/branch? loc))  (z/up loc) (rand-bottom-loc (rand-branch loc))))

(defn combine-node-branches [node1 node2]
  (if
   (and
    (z/branch? (z/vector-zip node1))
    (z/branch? (z/vector-zip node2)))
    (-> node1 (z/vector-zip) (rand-branch) (z/replace (rand-branch (z/vector-zip node2))) (z/root))
    node1))



;; MUTATE AND CROSSOVER TREES FUNCTIONS

(defn mutate-tree [tree]
  (strat/ameliorate-tree
   (let [n (rand-int 6)]
     (cond
       (= n 0) (-> tree (z/vector-zip) (rand-branch) (replace-rand-branch-with-rand-bool) (z/root))
       (= n 1) (-> tree (z/vector-zip) (rand-branch) (switch-branches) (z/root))
       (= n 2) (-> tree (z/vector-zip) (rand-bottom-loc) (new-rand-branch) (z/root))
       (= n 3) (-> tree (z/vector-zip) (rand-bottom-loc) (switch-branches) (z/root))
       (= n 4) (-> tree (z/vector-zip) (new-rand-branch) (z/root))
       (= n 5) (-> tree (z/vector-zip) (switch-branches) (z/root))))))

(defn get-rand-tree-branch [tree]
  (-> tree (z/vector-zip) (rand-branch) (z/node)))

(defn crossover-trees [tree1 tree2]
  (strat/ameliorate-tree
   (let [n (rand-int 4)]
     (cond
       (= n 0) (combine-node-branches tree1 tree2)
       (= n 1) (combine-node-branches (get-rand-tree-branch tree1) tree2)
       (= n 2) (combine-node-branches (get-rand-tree-branch tree2) tree1)
       (= n 3) (combine-node-branches (get-rand-tree-branch tree1) (get-rand-tree-branch tree2))))))

(defn get-strat-trees [strats]
  (for [strat strats]
    (strat :tree)))

(defn get-crossover-trees [trees num]
  (for [n (range num)]
    (crossover-trees 
     (rand-nth trees) 
     (rand-nth trees))))

(defn get-mutation-trees [trees num]
  (for [n (range num)]
    (mutate-tree (rand-nth trees))))

(defn populate-trees [trees input-and-target-streams]
  (for [tree trees]
    (vat/get-populated-strat-from-tree tree input-and-target-streams)))

;; RUN THROUGH

(def pop-size 10)
(def parent-pct 40)
(def crossover-pct 30)

(def num-parents (Math/round (double (* pop-size (/ parent-pct 100)))))
(def num-crossovers (Math/round (double (* pop-size (/ crossover-pct 100)))))
(def num-mutations (- pop-size num-parents num-crossovers))

(def input-and-target-streams (strat/get-input-and-target-streams 4 pop-size))

(def init-strats (get-populated-strats pop-size input-and-target-streams))

(def parent-strats (get-best-strats init-strats num-parents))
(def parent-trees (get-strat-trees parent-strats))

(def mutated-trees (get-mutation-trees parent-trees num-mutations))

(def crossover-trees (get-crossover-trees parent-trees num-crossovers))
(def crossover-strats (populate-trees crossover-trees input-and-target-streams))

(def new-pop
  (let [trees (get-strat-trees parent-strats)]
    (conj
     parent-strats
     (populate-trees (get-crossover-trees trees num-crossovers) input-and-target-streams)
     (populate-trees (get-mutation-trees trees num-mutations) input-and-target-streams))))


;; TODO
;; Build GA
    ;; 1. MAKE RANDOM STRATS
    ;; 2. GET FITNESS
    ;; 3. GET PARENTS (FITTEST N STRATEGIES)
    ;; 4. MAKE OFFSPRING (MUTATIONS AND CROSSOVERS OF PARENTS PLUS SOME NEW RANDOM ONES)
    ;; 5. RETURN TO STEP 2
;; When GA is working good, start building the "arena" *queue dramatic music*




