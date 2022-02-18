(ns v0_2_X.build_strategator
  (:require [stats :as stats]
            [clojure.pprint :as pp]
            [v0_2_X.solve_strategator :as sstgr]))
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
                    (with-meta #(Math/log (Math/abs (+ Math/E %))) {:name "modified log"})
                    (with-meta #(Math/abs %) {:name "abs"})))

(def many-arg-funcs
  [(with-meta (fn [& args] (apply + args)) {:name "+"})
   (with-meta (fn [& args] (apply * args)) {:name "*"})
   (with-meta (fn [& args] (apply max args)) {:name "max"})
   (with-meta (fn [& args] (apply min args)) {:name "min"})
   (with-meta (fn [& args] (mean args)) {:name "mean"})
   (with-meta (fn [& args] (stdev args)) {:name "stdev"})])
(def two-arg-funcs (cons (with-meta #(Math/pow %1 %2) {:name "pow"}) many-arg-funcs))

(def strategator-config {:min-depth 3 :max-depth 5 :max-children 10})

(defn make-strategator-recur
  ([config current-depth]
   (if (and (>= current-depth (get config :min-depth)) (or (> (rand) 0.5) (= current-depth (get config :max-depth))))
     {:id 0 :shift (first (random-sample 0.333 (range)))}
     (let [num-inputs (or (first (random-sample 0.25 (range (get config :max-children)))) 0)
           inputs (vec (repeatedly num-inputs #(rand-nth [{:id 0 :shift (first (random-sample 0.333 (range)))} (make-strategator-recur config (inc current-depth))])))
           func (cond
                  (= num-inputs 0) (rand)
                  (= num-inputs 1) (rand-nth one-arg-funcs)
                  (= num-inputs 2) (rand-nth two-arg-funcs)
                  (> num-inputs 2) (rand-nth many-arg-funcs))]
       {:fn-name (get (meta func) :name)
        :fn func
        :inputs inputs}))))

(def strategator-b (make-strategator-recur strategator-config 0))

(pp/pprint strategator-b)

(println (sstgr/solve-strategator strategator-b sstgr/num-data-points))
