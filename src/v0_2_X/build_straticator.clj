(ns v0_2_X.build_straticator
  (:require [stats :as stats]
            [clojure.pprint :as pp]
            [v0_2_X.solve_straticator :as sstcr]))
(defn mean
  ([vs] (mean (reduce + vs) (count vs)))
  ([sm sz] (/ sm sz)))
(defn stdev
  ([vs]
   (stdev vs (count vs) (mean vs)))
  ([vs size mu]
   (Math/sqrt (/ (apply + (map #(Math/pow (- % mu) 2) vs))
                 size))))

(def one-arg-funcs (list #(Math/sin %) #(Math/cos %) #(Math/log %) #(Math/abs %) #(Math/exp %)))
(def many-arg-funcs
  [(with-meta (fn [& args] (apply + args)) {:name "+"})
   (with-meta (fn [& args] (apply * args)) {:name "*"})
   (with-meta (fn [& args] (apply max args)) {:name "max"})
   (with-meta (fn [& args] (apply min args)) {:name "min"})
   (with-meta (fn [& args] (mean args)) {:name "mean"})
   (with-meta (fn [& args] (stdev args)) {:name "stdev"})])
(def two-arg-funcs (cons (with-meta #(Math/pow %1 %2) {:name "pow"}) many-arg-funcs))

(def straticator-config {:min-depth 3 :max-depth 5 :max-children 10})

(defn make-straticator-recur
  ([config current-depth]
   (if (and (>= current-depth (get config :min-depth)) (or (> (rand) 0.5) (= current-depth (get config :max-depth))))
     {:id 0 :shift (rand-int sstcr/num-data-points)}
     (let [num-inputs (+ 1 (rand-int (get config :max-children)))
           inputs (vec (repeatedly num-inputs #(rand-nth [{:id 0 :shift (rand-int 2)} (make-straticator-recur config (inc current-depth))])))
           func (cond
                  (= num-inputs 1) (rand-nth one-arg-funcs)
                  (= num-inputs 2) (rand-nth two-arg-funcs)
                  (> num-inputs 2) (rand-nth many-arg-funcs))]
       {:straticator-fn
        {:inputs inputs
         :fn func
         :fn-name (get (meta func) :name)}}))))

(def straticator-b (make-straticator-recur straticator-config 0))

(pp/pprint straticator-b)

(println (sstcr/solve-straticator straticator-b sstcr/num-data-points))