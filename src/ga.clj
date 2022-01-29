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
   [vec_strategy :as vat]
   [strategy :as strat]))




;; PLOT ALL THE STRATEGIES RETURN FUNCTIONS WITH THE INPUT DATA

(defn plot-strats-with-input-target-streams [strats input-and-target-data]
  (apply strat/plot-strats-with-input-target-streams input-and-target-data strats)
  strats)

(defn plot-strats [strats]
  (apply strat/plot-strats strats)
  strats)

;; MAKE A BUNCH OF POPULATED STRATEGIES

(defn get-populated-strats [config]
  (loop [i 0 v (transient [])]
    (if (< i (config :num-parents))
      (recur (inc i) (conj! v (vat/get-populated-strat (config :input-and-target-streams))))
      (persistent! v))))

(defn get-strat-fitness [strat]
  (let [fitness (last (strat :return-stream))]
    (assoc strat :fitness fitness)))

(defn get-strats-fitnesses [strats]
  (for [strat strats]
    (get-strat-fitness strat)))

(defn get-best-strats [strats num]
  (take num (reverse (sort-by :fitness strats))))


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


(defn get-random-tree [num-inputs depth-vec]
  (vat/make-vec-tree (vat/get-input-indxs num-inputs) depth-vec))

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
  (if (z/branch? loc)
    (let [new-node (get-random-tree 4 [0 1 1])] (-> loc (rand-branch) (z/replace new-node) (z/up))) loc))

(defn switch-branches [loc]
  (if (z/branch? loc) (-> loc (z/append-child (-> loc (branchA) (z/node))) (branchA) (z/remove) (z/up)) loc))

(defn rand-bottom-loc
  "recursively dives a tree until it finds a bool, then returns it's parent node"
  [loc] (if (not (z/branch? loc))  (z/up loc) (rand-bottom-loc (rand-branch loc))))

(defn combine-node-branches [node1 node2]
  (if
   (and
    (z/branch? (z/vector-zip node1))
    (z/branch? (z/vector-zip node2)))
    (-> node1 (z/vector-zip) (rand-branch) (z/replace (-> node2 (z/vector-zip) (rand-branch) (z/node))) (z/root))
    node1))


;; MUTATE AND CROSSOVER TREES FUNCTIONS

(defn get-mutated-tree [tree]
  (strat/ameliorate-tree
   (let [n (rand-int 8)]
     (cond
       (= n 0) (-> tree (z/vector-zip) (replace-rand-branch-with-rand-bool) (z/root))
       (= n 1) (-> tree (z/vector-zip) (rand-branch) (replace-rand-branch-with-rand-bool) (z/root))
       (= n 2) (-> tree (z/vector-zip) (prune-rand-branch) (z/root))
       (= n 3) (-> tree (z/vector-zip) (rand-branch) (prune-rand-branch) (z/root))
       (= n 4) (-> tree (z/vector-zip) (new-rand-branch) (z/root))
       (= n 5) (-> tree (z/vector-zip) (rand-branch) (new-rand-branch) (z/root))
       (= n 6) (-> tree (z/vector-zip) (switch-branches) (z/root))
       (= n 7) (-> tree (z/vector-zip) (rand-branch) (switch-branches) (z/root))))))

(defn get-rand-tree-branch [tree]
  (-> tree (z/vector-zip) (rand-branch) (z/node)))

(defn get-crossover-tree [trees]
  (let [rand-trees (shuffle trees)]
    (let [tree1 (first rand-trees) tree2 (last rand-trees)]
      (strat/ameliorate-tree
       (let [n (rand-int 4)]
         (cond
           (= n 0) (combine-node-branches tree1 tree2)
           (= n 1) (combine-node-branches (get-rand-tree-branch tree1) tree2)
           (= n 2) (combine-node-branches (get-rand-tree-branch tree2) tree1)
           (= n 3) (combine-node-branches (get-rand-tree-branch tree1) (get-rand-tree-branch tree2))))))))

(defn get-strat-trees [strats]
  (for [strat strats]
    (strat :tree)))

(defn get-crossover-trees [trees num]
  (for [n (range num)]
    (get-crossover-tree trees)))

(defn get-mutated-trees [trees num]
  (for [n (range num)]
    (get-mutated-tree (rand-nth trees))))

(defn get-random-trees [num]
  (for [n (range num)]
    (get-random-tree 4 [0 2 6])))

(defn ameliorate-trees [trees]
  (for [tree trees]
    (vat/ameliorate-tree tree)))

(defn populate-trees [trees input-and-target-streams]
  (for [tree trees]
    (vat/get-populated-strat-from-tree tree input-and-target-streams)))

;; RUN THROUGH

(def num-data-points 100)
;; (def pop-size 50)

(defn product-int [whole pct] (Math/round (double (* whole pct))))

(defn  get-ga-config [num-data-points pop-size parent-pct crossover-pct mutation-pct input-and-target-streams]
  (assoc {:num-data-points num-data-points
          :pop-size pop-size
          :parent-pct parent-pct
          :crossover-pct crossover-pct
          :mutation-pct mutation-pct
          :input-and-target-streams input-and-target-streams} 
         :num-parents (product-int pop-size parent-pct)
         :num-children (product-int pop-size (- 1.0 parent-pct))))

(def input-config (strat/get-inputs-config 4 100 10 0.01 0 100))

(def input-and-target-streams (strat/get-input-and-target-streams input-config))

(def ga-config (get-ga-config 100 50 0.4 0.3 0.5 input-and-target-streams))

(defn get-init-pop [config]
  (get-strats-fitnesses (get-populated-strats config)))

(def init-pop (get-init-pop ga-config))
(plot-strats-with-input-target-streams init-pop input-and-target-streams)

;; FUNCTIONIZE ME CAP'N!
(defn duplicate-tree-check
  "returns test-tree if test-tree is different from all trees in source-trees else nil"
  [source-trees test-tree]
  (if (reduce #(if (= test-tree %2) (reduced true) %1) false source-trees) nil test-tree))

(defn get-child-tree
  "parent-trees must have count >= 2
   config (reprod-wt) is map of keys: {:crossover :mutation} which holds probabilities of the respective reproduction techniques being used"
  [parent-trees config]
  (let [n (rand)]
    parent-trees
    (cond
      (< n (config :crossover-pct)) (get-crossover-tree parent-trees)
      (< n (+ (config :crossover-pct) (config :mutation-pct))) (get-mutated-tree (rand-nth parent-trees))
      :else (get-random-tree 4 [0 2 6]))))

(defn get-children-trees [parent-trees config]
  (loop [v (transient (vec parent-trees))]
    (if (< (count v) (+ (config :num-children) (count parent-trees)))
      (recur
       (let [new-child (duplicate-tree-check parent-trees (vat/ameliorate-tree (get-child-tree parent-trees config)))]
         (if new-child (conj! v new-child) v)))
      (persistent! v))))

(defn ga-epoch
  "config is map of keys: {:num-parents :num-children :crossover-pct :mutation-pct}"
  [population config]
  (-> population
      (get-best-strats (config :num-parents))
      (get-strat-trees)
      (get-children-trees config)
      (populate-trees (config :input-and-target-streams))
      (get-strats-fitnesses)
      (plot-strats-with-input-target-streams (config :input-and-target-streams))))

;; (loop [i 0 pop init-pop]
;;   (let [next-gen (ga-epoch pop ga-config)]
;;     (if (< i 10) (recur (inc i) next-gen) next-gen)))

(defn run-epochs
  ([num-epochs] (run-epochs num-epochs init-pop ga-config))
  ([num-epochs population config]
   (loop [i 0 pop population]
     (let [next-gen (ga-epoch pop config)]
       (if (< i num-epochs) (recur (inc i) next-gen) next-gen)))))

(def best-strats (run-epochs 10))

;; TODO
;; Build GA ✅
    ;; 1. MAKE RANDOM STRATS ✅
    ;; 2. GET FITNESS ✅
    ;; 3. GET PARENTS (FITTEST N STRATEGIES) ✅
    ;; 4. MAKE OFFSPRING (MUTATIONS AND CROSSOVERS OF PARENTS PLUS SOME NEW RANDOM ONES) ✅
    ;; 5. RETURN TO STEP 2 ect ✅

;; When GA is working good, start building the "arena" *queue dramatic music*




