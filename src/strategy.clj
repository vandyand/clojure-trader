(ns strategy
  (:require
  ;;  [clojure.spec.alpha :as s]
  ;;  [clojure.spec.gen.alpha :as sgen]
  ;;  [clojure.test.check.generators :as gen]
  ;;  [clojure.string :as cs]
   [clojure.walk :as w]
   [oz.core :as oz]
   [clojure.set :as set]))

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

;; START SERVER FOR VISUALIZATION

(oz/start-server! 10667)


;; CONFIG SETTINGS
(def min-tree-depth 1)
(def max-tree-depth 4)
(def num-inputs 4)
(def num-data-points 100)
(def index-pairs
  (set (filter
        #(not= (first %) (last %))
        (for [x (range num-inputs) y (range num-inputs)] [x y]))))


;; MAKE TREE

(defn make-tree
  ([] (make-tree {} 0 #{}))
  ([tree depth index-pairs-used]
   (if (and (>= depth min-tree-depth) (or (> (rand) 0.5) (= depth max-tree-depth)))
     (rand-nth [1 0])
     (let [index-pair (rand-nth (vec (set/difference index-pairs index-pairs-used)))]
       (let [new-branch #(make-tree tree (inc depth) (set/union #{index-pair} index-pairs-used))]
         {:input-indxs index-pair
          :branchA (new-branch)
          :branchB (new-branch)})))))

(defn ameliorate-tree
  "Fixes condition where both branches of a node are true or both are false (which negates the meaning of the node)"
  [tree]
  (w/postwalk
   #(if (and
         (= (type %) clojure.lang.PersistentArrayMap)
         (= (type (% :branchA)) java.lang.Long)
         (= (% :branchA) (% :branchB)))
      (assoc % :branchB (mod (+ 1 (% :branchB)) 2))
      %)
   tree))

(defn print-tree [tree]
  (println tree)
  tree)

(def tree (print-tree (make-tree)))
(ameliorate-tree (make-tree))

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
       (tree :branchB)) inst-inputs)))


;; SOLVE TREE WITH RANDOM INPUTS

(def rand-inputs
  "Creates (is) zipped input streams (inputs cols instead of rows as it were if each input-stream were a row)"
  (map vec (partition num-inputs (take (* num-inputs num-data-points) (repeatedly #(rand))))))

(for [inst-inputs rand-inputs]
  (solve-tree (ameliorate-tree (make-tree)) inst-inputs))


;; CODIFY INPUT DATA FUNCTIONS

(defn rand-caps-str [len]
  (apply str (take len (repeatedly #(char (+ (rand 26) 65))))))

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
  ([] (get-random-sine-stream (str "stream " (rand-caps-str 5))))
  ([name]
   (with-meta
     (mapv
      (get-stream-gen-fn)
      (range num-data-points))
     {:name name})))

(defn zip-input-streams [& streams]
  (loop [i 0 v (transient [])]
    (if (< i num-data-points)
      (recur (inc i) (conj! v (vec (for [stream streams] (stream i)))))
      (persistent! v))))


;; VISUALIZATION FORMATTING FUNCTION

(defn format-stream-for-view
  "returns a collection of view data (maps) of form {:item <stream name> :x <x input angle> :y <stream solution at x>} from the stream"
  [stream]
  (let [item  ((meta stream) :name)]
    (loop [i 0 v (transient [])]
      (if (< i num-data-points)
        (recur (inc i) (conj! v {:item item :x i :y (stream i)}))
        (persistent! v)))))


;; GET RANDOM SINE WAVES AS INPUT STEAMS AND TARGET STREAM

(time
 (do
   (def input-streams (repeatedly num-inputs #(get-random-sine-stream)))

   (def target-stream (get-random-sine-stream))

   (def target-stream-delta
     (with-meta
       (into [0.0]
             (for [i (range (- (count target-stream) 1))]
               (- (target-stream (+ i 1)) (target-stream i))))
       {:name "target stream deltas"}))))


;; GET STRATEGY FUNCTIONS

(defn get-strat-tree [] (ameliorate-tree (make-tree)))

(defn get-sieve-stream
  [name input-streams strat-tree]
  (with-meta (vec (for [inputs (apply zip-input-streams input-streams)]
                    (solve-tree strat-tree inputs))) {:name name}))

(defn get-return-stream [name sieve-stream target-stream-delta]
  (with-meta
    (loop [i 1 v (transient [0.0])]
      (if (< i num-data-points)
        (recur (inc i) (conj! v (+ (v (- i 1)) (* (sieve-stream (- i 1)) (target-stream-delta i)))))
        (persistent! v))) {:name name}))

(defn get-populated-strat [name]
  (let [tree (get-strat-tree)]
    (let [sieve-stream (get-sieve-stream (str name " sieve stream") input-streams tree)]
      (let [return-stream (get-return-stream (str name " return stream") sieve-stream target-stream-delta)]
        {:name name :tree tree :sieve-stream sieve-stream :return-stream return-stream}))))


;; CREATE MULTIPLE STRATEGIES EACH YEILDING A RETURN STREAM

(def strat (get-populated-strat "strat 1"))

(def streams (conj input-streams target-stream (strat :sieve-stream) (strat :return-stream)))

(def view-data (flatten (map format-stream-for-view streams)))

(def line-plot
  {:data {:values view-data}
   :encoding {:x {:field "x" :type "quantitative"}
              :y {:field "y" :type "quantitative"}
              :color {:field "item" :type "nominal"}}
   :mark {:type "line"}})

(def viz
  [:div [:vega-lite line-plot {:width 500}]])

(oz/view! viz)

;; Maybe start a new file?
;; Generate a batch of return streams from a batch of strategy trees
;; Start going on GA
;; When GA is working good, start building the "arena" *queue dramatic music*