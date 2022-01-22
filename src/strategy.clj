(ns strategy
  (:require
  ;;  [clojure.spec.alpha :as s]
  ;;  [clojure.spec.gen.alpha :as sgen]
  ;;  [clojure.test.check.generators :as gen]
   [clojure.string :as cs]
   [clojure.walk :as w]
   [oz.core :as oz]
   [clojure.set :as set]))

(comment
  "In this file we randomly generate a recursive strategy tree (each node being a map of {:input-indxs :branchA :branchB}) and then solve it recursively"
;; Example tree:
;;  {:input-indxs [4 0], 
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
;;                                :branchB false}}}}
  )

;; START SERVER FOR VISUALIZATION

(oz/start-server! 10667)


;; CONFIG SETTINGS
;; (def min-tree-depth 1)
;; (def max-tree-depth 4)
(def num-inputs 4)
(def num-data-points 100)
(defn index-pairs [num-inputs]
  (set (filter
        #(not= (first %) (last %))
        (for [x (range num-inputs) y (range num-inputs)] [x y]))))


;; MAKE TREE
(defn isArrayMap? [testee] (= (type testee) clojure.lang.PersistentArrayMap))
(defn isLong? [testee] (= (type testee) java.lang.Long))

(defn make-raw-tree
  ([] (make-raw-tree {} 0 2 6 (index-pairs num-inputs) #{}))
  ([tree depth min-depth max-depth index-pairs index-pairs-used]
   (if (and (>= depth min-depth) (or (> (rand) 0.5) (= depth max-depth)))
     (rand-nth [1 0])
     (let [index-pair (rand-nth (vec (set/difference index-pairs index-pairs-used)))]
       (let [new-branch #(make-raw-tree tree (inc depth) min-depth max-depth index-pairs (set/union #{index-pair} index-pairs-used))]
         {:input-indxs index-pair
          :branchA (new-branch)
          :branchB (new-branch)})))))

(defn ameliorate-tree
  "Fixes condition where both branches of a node are true or both are false (which negates the meaning of the node)"
  [tree]
  (w/postwalk
   #(if (and
         (isArrayMap? %)
         (isLong? (% :branchA))
         (= (% :branchA) (% :branchB)))
      (assoc % :branchB (mod (+ 1 (% :branchB)) 2))
      %)
   tree))

(defn make-tree 
  ([] (ameliorate-tree (make-raw-tree)))
  ([& args] (ameliorate-tree (apply make-raw-tree args))))

(defn print-tree [tree]
  (print (cs/replace (str tree) ":b" "\n:b")))

;; (def tree (print-tree (make-tree)))
;; (ameliorate-tree (make-tree))

;; SOLVE TREE FUNCTIONS

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
       (tree :branchB)) 
     inst-inputs)))


;; SOLVE TREE WITH RANDOM INPUTS

(def rand-inputs
  "Creates (is) zipped input streams (inputs cols instead of rows as it were if each input-stream were a row)"
  (map vec (partition num-inputs (take (* num-inputs num-data-points) (repeatedly #(rand))))))

;; (for [inst-inputs rand-inputs]
;;   (solve-tree (ameliorate-tree (make-tree)) inst-inputs))


;; CODIFY INPUT DATA FUNCTIONS

(defn rand-caps-str [len]
  (apply str (take len (repeatedly #(char (+ (rand 26) 65))))))

(defn rand-suffix [input-str]
  (str input-str "-" (rand-caps-str 10)))

(defn scaled-rand-dbl
  "returns random double between min (inclusive) and max (exclusive)"
  [min max]
  (-> (- max min) (rand) (+ min)))

(defn get-stream-gen-fn []
  (fn [x]
    (-> x
        (* (scaled-rand-dbl 0 0.01)) ;; freq
        (- (scaled-rand-dbl 0 100)) ;; h-shift
        (Math/sin)
        (* (scaled-rand-dbl 0 10)) ;; amp
        (+ (scaled-rand-dbl 0 0)))) ;; v-shift
  )

(defn get-random-sine-stream
  ([num-data-points] (get-random-sine-stream (rand-suffix "stream") num-data-points))
  ([name num-data-points]
   (with-meta
     (mapv
      (get-stream-gen-fn)
      (range num-data-points))
     {:name name})))

(defn zip-input-streams [& streams]
  (loop [i 0 v (transient [])]
    (if (< i (count (first streams)))
      (recur (inc i) (conj! v (vec (for [stream streams] (stream i)))))
      (persistent! v))))


;; VISUALIZATION FORMATTING FUNCTION

(defn format-stream-for-view
  "returns a collection of view data (maps) of form {:item <stream name> :x <x input angle> :y <stream solution at x>} from the stream"
  [stream]
  (let [item  ((meta stream) :name)]
    (loop [i 0 v (transient [])]
      (if (< i (count stream))
        (recur (inc i) (conj! v {:item item :x i :y (stream i)}))
        (persistent! v)))))


;; GET (AND POPULATE) STRATEGY FUNCTIONS

(defn get-sieve-stream
  [name input-streams strat-tree solve-tree-fn]
  (with-meta (vec (for [inputs (apply zip-input-streams input-streams)]
                    (solve-tree-fn strat-tree inputs))) {:name name}))

(defn get-return-stream [name sieve-stream target-stream-delta]
  (with-meta
    (loop [i 1 v (transient [0.0])]
      (if (< i (count sieve-stream))
        (recur (inc i) (conj! v (+ (v (- i 1)) (* (sieve-stream (- i 1)) (target-stream-delta i)))))
        (persistent! v))) {:name name}))

(defn get-populated-strat-from-tree [tree input-and-target-streams solve-tree-fn]
  (let [name (rand-suffix "strat")]
   (let [sieve-stream (get-sieve-stream (str name " sieve stream") (input-and-target-streams :input-streams) tree solve-tree-fn)]
       (let [return-stream (get-return-stream (str name " return stream") sieve-stream (input-and-target-streams :target-stream-delta))]
           {:name name :tree tree :sieve-stream sieve-stream :return-stream return-stream}))))

(defn get-populated-strat
  ([input-and-target-streams] (get-populated-strat input-and-target-streams make-tree solve-tree))
  ([input-and-target-streams make-tree-fn solve-tree-fn]
   (let [tree (make-tree-fn)]
     (get-populated-strat-from-tree tree input-and-target-streams solve-tree-fn))))


;; GET INPUT STREAMS AND TARGET DELTA STREAM FUNCTIONS

(defn get-input-streams [num-streams num-data-points]
  (repeatedly num-streams #(get-random-sine-stream num-data-points)))

(defn get-target-stream-delta [target-stream]
  (with-meta
    (into [0.0]
          (for [i (range (- (count target-stream) 1))]
            (- (target-stream (+ i 1)) (target-stream i))))
    {:name "target stream deltas"}))

(defn get-input-and-target-streams [num-inputs num-data-points]
  (let [input-streams (get-input-streams num-inputs num-data-points)]
    (let [target-stream (with-meta (rand-nth input-streams) {:name "target stream"})]
      {:input-streams input-streams :target-stream target-stream :target-stream-delta (get-target-stream-delta target-stream)})))


;; CREATE POPULATED STRATEGY AND VIEW PLOT

(defn get-plot-streams [input-and-target-streams & strats]
  (let [plot-streams (transient (vec (conj (input-and-target-streams :input-streams) (input-and-target-streams :target-stream))))]
    (loop [i 0 v plot-streams]
      (if (< i (count strats))
        (recur (inc i) (conj! v ((nth strats i) :return-stream)))
        (persistent! v)))))

(defn get-plot-values [plot-streams]
  (flatten
   (map
    format-stream-for-view
    plot-streams)))

(defn generate-plot [values]
  (let [viz
        [:div
         [:vega-lite
          {:data
           {:values values}
           :encoding {:x {:field "x" :type "quantitative"}
                      :y {:field "y" :type "quantitative"}
                      :color {:field "item" :type "nominal"}}
           :mark {:type "line"}} {:width 500}]]]

    (oz/view! viz)))

(defn plot-strats [input-and-target-streams & strats]
  (generate-plot
   (get-plot-values
    (apply get-plot-streams input-and-target-streams strats))))

(def input-and-target-streams (get-input-and-target-streams num-inputs num-data-points))

(time
 (do
   (def strat1 (get-populated-strat input-and-target-streams))
   (def strat2 (get-populated-strat input-and-target-streams))
   (def strat3 (get-populated-strat input-and-target-streams))
   (def strat4 (get-populated-strat input-and-target-streams))
(plot-strats input-and-target-streams strat1 strat2 strat3 strat4)))

