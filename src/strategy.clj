(ns strategy
  (:require
  ;;  [clojure.spec.alpha :as s]
  ;;  [clojure.spec.gen.alpha :as sgen]
  ;;  [clojure.test.check.generators :as gen]
  ;;  [clojure.string :as cs]
   [clojure.walk :as w]))

(comment
  "In this file we randomly generate a strategy (tree) and then solve it recursively"

 ; just make the function that returns the tree?
;; (def tree {:cond #(> (nth inputs 1) (nth inputs 2)) 
;;            :branchA {:cond #(> (nth inputs 0) (nth inputs 1))
;;                      :branchA {:cond #(> (nth inputs 0) (nth inputs 3)) :branchA true :branchB false} 
;;                      :branchB {:cond #(> (nth inputs 3) (nth inputs 1)) :branchA false :branchB true}} 
;;            :branchB {:cond #(> (nth inputs 3) (nth inputs 2)) 
;;                      :branchA false 
;;                      :branchB {:cond #(> (nth inputs 0) (nth inputs 2)) :branchA true :branchB false}}})

; Another example tree
;;   (def tree {:input-indxs [4 0], 
;;  :branchA {:input-indxs [3 4], 
;;            :branchA {:input-indxs [2 3], 
;;                      :branchA {:input-indxs [2 0], 
;;                                :branchA true, 
;;                                :branchB {:input-indxs [3 1], 
;;                                          :branchA true, 
;;                                          :branchB {:input-indxs [3 3], 
;;                                                    :branchA true, 
;;                                                    :branchB false}}}, 
;;                      :branchB false}, 
;;            :branchB {:input-indxs [2 3], 
;;                      :branchA {:input-indxs [4 3], 
;;                                :branchA false, 
;;                                :branchB true}, 
;;                      :branchB false}}, 
;;  :branchB {:input-indxs [3 3], 
;;            :branchA {:input-indxs [1 0], 
;;                      :branchA false, 
;;                      :branchB false}, 
;;            :branchB {:input-indxs [1 3], 
;;                      :branchA {:input-indxs [3 2], 
;;                                :branchA false, 
;;                                :branchB false}, 
;;                      :branchB {:input-indxs [1 0], 
;;                                :branchA true, 
;;                                :branchB false}}}})
  )

;; GET (MAKE, TRIM AND PRINT) TREE
(def max-tree-depth 4)
(def num-inputs 4)
(def num-data-points 10)
(def index-pairs
  (filter
   #(not= (first %) (last %))
   (for [x (range num-inputs) y (range num-inputs)] [x y])))

(defn make-tree
  ([] (make-tree {} 0))
  ([tree] tree)
  ([tree depth]
   (if (or (> (rand) 0.5) (= depth max-tree-depth))
     (rand-nth [true false])
     {:input-indxs (rand-nth index-pairs)
      :branchA (make-tree tree (inc depth))
      :branchB (make-tree tree (inc depth))})))

(defn trim-tree [tree]
  (w/postwalk
   #(if
     (and
      (= (type %) clojure.lang.PersistentArrayMap)
      (= (% :branchA) (% :branchB)))
      (% :branchA)
      %)
   tree))

(defn print-tree [tree]
  (println tree)
  tree)

(def tree (print-tree (trim-tree (make-tree))))

;; SOLVE TREE WITH RANDOM INPUT DATA
(def rand-inputs (mapv vec (partition num-inputs (take (* num-inputs num-data-points) (repeatedly #(rand))))))

(defn solve-cond [inputs input-indxs]
  (> (inputs (first input-indxs)) (inputs (last input-indxs))))

(defn solve-tree [tree inputs]
  (println inputs)
  (if (= (type tree) java.lang.Boolean)
    tree
    (solve-tree
     (if (solve-cond inputs (tree :input-indxs))
       (tree :branchA)
       (tree :branchB)) inputs)))

(println rand-inputs)

(for [inputss rand-inputs]
  (solve-tree tree inputss))

;; CODIFY INPUT DATA

(defn get-random-input-stream
  ([] (get-random-input-stream nil))
  ([name]
   (with-meta
     (vec (map (rand-nth [#(Math/sin %) #(Math/cos %) #(Math/tan %) #(/ % 10) #(/ % -10)]) (range num-data-points)))
     {:name name})))

(defn zip-input-streams [& streams]
  (loop [i 0 v (transient [])]
    (if (< i num-data-points)
      (recur (inc i) (conj! v (vec (for [stream streams] (stream i)))))
      (persistent! v))))

(def inputs)

(for 
 [inputs 
  (apply 
   zip-input-streams 
   (repeatedly 
    num-inputs 
    #(get-random-input-stream)))]
  (println inputs))
  ;; (solve-tree tree inputs))


(defn format-stream-for-view [stream]
  (let [item  ((meta stream) :name)]
    (loop [i 0 v (transient [])]
      (if (< i num-data-points)
        (recur (inc i) (conj! v {:item item :x i :y (stream i)}))
        (persistent! v)))))



(def view-data
  (into [] (concat
            (format-stream-for-view input-stream-1)
            (format-stream-for-view input-stream-2)
            (format-stream-for-view sieve-stream)
            (format-stream-for-view return-stream))))

(def line-plot
  {:data {:values view-data}
   :encoding {:x {:field "x" :type "quantitative"}
              :y {:field "y" :type "quantitative"}
              :color {:field "item" :type "nominal"}}
   :mark {:type "line"}})

(def viz
  [:div [:vega-lite line-plot {:width 500}]])

(oz/view! viz)


