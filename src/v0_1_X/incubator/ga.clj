(ns v0_1_X.incubator.ga
  (:require
   [clojure.pprint :as pp]
  ;;  [clojure.spec.alpha :as s]
  ;;  [clojure.spec.gen.alpha :as sgen]
  ;;  [clojure.test.check.generators :as gen]
  ;;  [clojure.string :as cs]
  ;;  [clojure.walk :as w]
   [clojure.zip :as z]
  ;;  [oz.core :as oz]
  ;;  [clojure.set :as set]
   [v0_1_X.incubator.strategy :as strat]
   [v0_1_X.incubator.inputs :as inputs]
   [v0_2_X.strindicator :as strindy]))

;; CONFIG FUNCTIONS

(defn product-int [whole pct] (Math/round (double (* whole pct))))

(defn  get-pop-config [pop-size parent-pct crossover-pct mutation-pct]
  (assoc {:pop-size pop-size
          :parent-pct parent-pct
          :crossover-pct crossover-pct
          :mutation-pct mutation-pct}
         :num-parents (product-int pop-size parent-pct)
         :num-children (product-int pop-size (- 1.0 parent-pct))))

(defn get-ga-config [num-epochs input-config tree-config pop-config]
  {:num-epochs num-epochs
   :input-config input-config
   :tree-config tree-config
   :pop-config pop-config})

;; PLOT ALL THE STRATEGIES RETURN FUNCTIONS WITH THE INPUT DATA

(defn plot-strats-and-inputs [strats input-config]
  (apply strat/plot-strats-and-inputs input-config strats)
  strats)

(defn plot-strats [strats]
  (apply strat/plot-strats strats)
  strats)

;; MAKE A BUNCH OF POPULATED STRATEGIES

(defn get-populated-strats [ga-config]
  (loop [i 0 v (transient [])]
    (if (< i (get-in ga-config [:pop-config :num-parents]))
      (recur (inc i)
             (conj! v (strat/get-populated-strat
                       (get ga-config :input-config)
                       (get ga-config :tree-config))))
      (persistent! v))))

(defn get-strat-fitness [strat]
  (let [fitness (last (last (strat :return-streams)))]
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

(defn prune-rand-branch [loc]
  (if (z/branch? loc) (-> loc (z/replace (-> loc (rand-branch) (z/node))))
      loc))

(defn replace-rand-branch-with-rand-bool [loc]
  (if (z/branch? loc) (-> loc (rand-branch) (z/replace (rand-bool)) (z/up))
      loc))

(defn new-rand-branch [loc]
  (if (z/branch? loc)
    (let [subtree-config (strat/get-tree-config 0 1 2)
          new-node (strat/make-tree-recur subtree-config)]
      (-> loc (rand-branch) (z/replace new-node) (z/up))) loc))

(defn switch-branches [loc]
  (if (z/branch? loc) (-> loc (z/append-child (-> loc (branchA) (z/node)))
                          (branchA) (z/remove) (z/up)) loc))

(defn rand-bottom-loc
  "recursively dives a tree until it finds a bool, then returns it's 
   parent node"
  [loc] (if (not (z/branch? loc))  (z/up loc) (rand-bottom-loc
                                               (rand-branch loc))))

(defn combine-node-branches [node1 node2]
  (if
   (and
    (z/branch? (z/vector-zip node1))
    (z/branch? (z/vector-zip node2)))
    (-> node1
        (z/vector-zip)
        (rand-branch)
        (z/replace (-> node2 (z/vector-zip) (rand-branch) (z/node)))
        (z/root))
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
  (let [rand-trees (shuffle trees)
        tree1 (first rand-trees)
        tree2 (last rand-trees) 
        n (rand-int 4)]
    (strat/ameliorate-tree
     (cond
       (= n 0) (combine-node-branches tree1 tree2)
       (= n 1) (combine-node-branches (get-rand-tree-branch tree1) tree2)
       (= n 2) (combine-node-branches (get-rand-tree-branch tree2) tree1)
       (= n 3) (combine-node-branches (get-rand-tree-branch tree1)
                                      (get-rand-tree-branch tree2))))))

(defn get-strat-trees [strats]
  (for [strat strats]
    (get strat :tree)))

(defn get-crossover-trees [trees num]
  (repeatedly num (get-crossover-tree trees)))

(defn get-mutated-trees [trees num]
  (repeatedly num (get-mutated-tree (rand-nth trees))))

(defn get-random-trees [num config]
  (repeatedly num (strat/make-tree-recur config)))

(defn ameliorate-trees [trees]
  (for [tree trees]
    (strat/ameliorate-tree tree)))

(defn populate-trees [trees input-config]
  (for [tree trees]
    (strat/get-populated-strat-from-tree tree input-config)))

;; RUN THROUGH

(defn get-init-pop [ga-config]
  (get-strats-fitnesses (get-populated-strats ga-config)))

;; FUNCTIONIZE ME CAP'N!
(defn duplicate-tree-check
  "returns test-tree if test-tree is different from all trees in 
   source-trees else nil"
  [source-trees test-tree]
  (if (reduce #(if (= test-tree %2) (reduced true) %1) false source-trees)
    nil test-tree))

(defn get-child-tree
  "parent-trees must have count >= 2
   config (reprod-wt) is map of keys: {:crossover :mutation} which holds
   probabilities of the respective reproduction techniques being used"
  [parent-trees pop-config tree-config]
  (let [n (rand)]
    parent-trees
    (cond
      (< n (get pop-config :crossover-pct))
      (get get-crossover-tree parent-trees)
      (< n (+ (get pop-config :crossover-pct)
              (get pop-config :mutation-pct)))
      (get-mutated-tree (rand-nth parent-trees))
      :else (strat/make-tree-recur tree-config))))

(defn get-children-trees [parent-trees ga-config]
  (loop [v (transient (vec parent-trees))]
    (if (< (count v) (+ (get-in ga-config [:pop-config :num-children])
                        (count parent-trees)))
      (recur
       (let [new-child (duplicate-tree-check
                        parent-trees
                        (strat/ameliorate-tree
                         (get-child-tree
                          parent-trees
                          (get ga-config :pop-config)
                          (get ga-config :tree-config))))]
         (if new-child (conj! v new-child) v)))
      (persistent! v))))

(defn run-epoch
  "config is map of keys: {:num-parents :num-children :crossover-pct :mutation-pct}"
  [population ga-config]
  (-> population
      (get-best-strats (get-in ga-config [:pop-config :num-parents]))
      (get-strat-trees)
      (get-children-trees ga-config)
      (populate-trees (get ga-config :input-config))
      (get-strats-fitnesses)))

(defn run-epochs
  ([ga-config] (run-epochs (get-init-pop ga-config) ga-config))
  ([population ga-config]
   (loop [i 0 pop population]
     (let [next-gen (run-epoch pop ga-config)
           best-score (get (first next-gen) :fitness)
           average (let [fitnesses (map :fitness next-gen)]
                     (/ (reduce + fitnesses) (count fitnesses)))]
       (println "gen  " i " best score: " best-score
                " avg pop score: " average)
       (if (< i (get ga-config :num-epochs)) (recur (inc i) next-gen) next-gen)))))


(def ga-config
  (let [num-epochs 10
        input-config (inputs/get-sine-inputs-config 10 1 200 10 0.1 0.1 100)
        tree-config (strat/get-tree-config
                     3 6 (count (get input-config :inception-streams-config)))
        pop-config (get-pop-config 50 0.5 0.4 0.5)]
    (get-ga-config num-epochs input-config tree-config pop-config)))

(def best-pop (run-epochs ga-config))
(plot-strats-and-inputs (take 5 best-pop)
                        (get ga-config :input-config))
(strat/get-strats-info (take 5 best-pop))


;;---------------------------------------;;---------------------------------------;;---------------------------------------;;---------------------------------------

;; (def ga-config
;;   (let [num-epochs 10
;;         strindy-config (strindy/get-strindy-config 5 5 6 [0 1] [1])
;;         input-config (strindy/get-strindy-inputs-config 10 1 100 strindy-config)
;;         tree-config (strat/get-tree-config
;;                      3 6 (count (get input-config :inception-streams-config)))
;;         pop-config (get-pop-config 50 0.5 0.4 0.5)]
;;     (get-ga-config num-epochs input-config tree-config pop-config)))

;; (def best-pop (run-epochs ga-config))

;; (plot-strats-and-inputs (take 5 best-pop)
;;                         (get ga-config :input-config))
;; (strat/get-strats-info (take 5 best-pop))