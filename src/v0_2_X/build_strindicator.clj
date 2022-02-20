(ns v0_2_X.build_strindicator
  (:require [stats :as stats]
            [clojure.pprint :as pp]
            [v0_2_X.solve_strindicator :as s-strind]
            ;; [v0_1_X.incubator.strategy :as strat]
            ))


(defn mean
  ([vs] (mean (reduce + vs) (count vs)))
  ([sm sz] (/ sm sz)))

(defn stdev
  ([vs]
   (stdev vs (count vs) (mean vs)))
  ([vs size mu]
   (Math/sqrt (/ (apply + (map #(Math/pow (- % mu) 2) vs))
                 size))))

(def one-arg-funcs (list
                    (with-meta #(Math/sin %) {:name "sin"})
                    (with-meta #(Math/cos %) {:name "cos"})
                    (with-meta #(Math/tan %) {:name "tan"})
                    (with-meta #(Math/log (Math/abs (+ Math/E %))) {:name "modified log"})
                    ;; (with-meta #(Math/abs %) {:name "abs"})
                    ))

(def many-arg-funcs
  [(with-meta (fn [& args] (apply + args)) {:name "+"})
   (with-meta (fn [& args] (apply * args)) {:name "*"})
   (with-meta (fn [& args] (apply max args)) {:name "max"})
   (with-meta (fn [& args] (apply min args)) {:name "min"})
   (with-meta (fn [& args] (mean args)) {:name "mean"})
   (with-meta (fn [& args] (stdev args)) {:name "stdev"})])

(def two-arg-funcs (cons (with-meta #(Math/pow %1 %2) {:name "pow"}) many-arg-funcs))

(def strindicator-config {:min-depth 3 :max-depth 3 :max-children 5 :subscription-ids [0 1]})

;; (defn binary-func [num-inputs] 
;;   (with-meta 
;;     (fn [& args] 
;;       (strat/solve-tree 
;;        (strat/make-tree (strat/get-tree-config 3 5 (strat/get-index-pairs num-inputs))) 
;;        [args])) 
;;     {:name "strat tree"}))

(defn make-strindicator-recur
  ([config current-depth]
   (if (and (>= current-depth (get config :min-depth)) (or (> (rand) 0.5) (= current-depth (get config :max-depth))))
     (rand-nth [{:id (rand-nth (get config :subscription-ids)) :shift (first (random-sample 0.5 (range)))} {:fn-name "rand constant" :fn (rand) :inputs []}])
     (let [max-children (get config :max-children)
           new-depth (inc current-depth)
           num-inputs (or (first (random-sample 0.5 (range 1 max-children))) max-children)
           inputs (vec (repeatedly num-inputs #(make-strindicator-recur config new-depth)))
           func (cond
                  ;; (= current-depth 0) (binary-func num-inputs)
                  (= num-inputs 0) (rand)
                  (= num-inputs 1) (rand-nth one-arg-funcs)
                  (= num-inputs 2) (rand-nth two-arg-funcs)
                  (> num-inputs 2) (rand-nth many-arg-funcs))]
       {:fn-name (get (meta func) :name)
        :fn func
        :inputs inputs}))))

(def strindicator-b (make-strindicator-recur strindicator-config 0))

(pp/pprint strindicator-b)

(println (s-strind/solve-strindicator strindicator-b 20))