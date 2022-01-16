(ns strategy
  (:require
  ;;  [clojure.spec.alpha :as s]
  ;;  [clojure.spec.gen.alpha :as sgen]
  ;;  [clojure.test.check.generators :as gen]
  ;;  [clojure.string :as cs]
   [clojure.walk :as w]
   [oz.core :as oz]))

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
(def max-tree-depth 3)
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
     (rand-nth [1 0])
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

(defn solve-cond [inputs input-indxs]
  (> (inputs (first input-indxs)) (inputs (last input-indxs))))

(defn solve-tree 
  "Solves tree for one 'moment in time'. inst-inputs (instance (or instant?) inputs) refers to the nth index of each input stream"
  [tree inst-inputs]
  (if (= (type tree) java.lang.Long)
    tree
    (solve-tree
     (if (solve-cond inst-inputs (tree :input-indxs))
       (tree :branchA)
       (tree :branchB)) inst-inputs)))

(def rand-inputs 
  "Creates (is) zipped input streams (inputs cols instead of rows as it were if each input-stream were a row)"
  (map vec (partition num-inputs (take (* num-inputs num-data-points) (repeatedly #(rand))))))

(for [inst-inputs rand-inputs]
  (solve-tree tree inst-inputs))

;; CODIFY INPUT DATA
(defn rand-caps-str [len]
  (apply str (take len (repeatedly #(char (+ (rand 26) 65))))))

(defn get-random-input-stream
  ([] (get-random-input-stream (str "input stream " (rand-caps-str 5))))
  ([name]
   (with-meta
     (mapv (rand-nth [#(Math/sin %) #(* 1.1 (Math/sin %)) #(* 0.9 (Math/sin %)) #(* 1.1 (Math/cos %)) #(* 0.9 (Math/cos %)) #(Math/cos %) #(Math/tan %) #(/ % 10) #(/ % -10)]) (range num-data-points))
     {:name name})))

(defn zip-input-streams [& streams]
  (loop [i 0 v (transient [])]
    (if (< i num-data-points)
      (recur (inc i) (conj! v (vec (for [stream streams] (stream i)))))
      (persistent! v))))

(def input-streams (repeatedly num-inputs #(get-random-input-stream)))

(def sieve-stream
  (with-meta (vec (for [inputs (apply zip-input-streams input-streams)]
    (solve-tree tree inputs))) {:name "sieve stream"}))

(def target-stream (with-meta (rand-nth input-streams) {:name "target stream"}))

(def target-stream-delta
  (with-meta
    (into [0.0]
          (for [i (range (- (count target-stream) 1))]
            (- (target-stream (+ i 1)) (target-stream i))))
    {:name "target stream deltas"}))

(def return-stream
  (with-meta
    (loop [i 1 v (transient [0.0])]
      (if (< i 10)
        (recur
         (inc i)
         (conj! v
                (+
                 (v
                  (- i 1))
                 (*
                  (sieve-stream
                   (- i 1))
                  (target-stream-delta i)))))
        (persistent! v))) {:name "return stream"}))


(defn format-stream-for-view 
  "returns a collection of view data (maps) from the stream"
  [stream]
  (let [item  ((meta stream) :name)]
    (loop [i 0 v (transient [])]
      (if (< i num-data-points)
        (recur (inc i) (conj! v {:item item :x i :y (stream i)}))
        (persistent! v)))))

(def streams (conj input-streams sieve-stream return-stream))

(def view-data (mapv format-stream-for-view streams))

(def line-plot
  {:data {:values (flatten view-data)}
   :encoding {:x {:field "x" :type "quantitative"}
              :y {:field "y" :type "quantitative"}
              :color {:field "item" :type "nominal"}}
   :mark {:type "line"}})

(def viz
  [:div [:vega-lite line-plot {:width 500}]])


(oz/start-server! 10667)

(oz/view! viz)


