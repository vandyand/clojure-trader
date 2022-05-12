(ns v0_1_X.strategy
  (:require
   [clojure.pprint :as pp]
   [clojure.walk :as w]
   [clojure.zip :as z]
   [oz.core :as oz]
   [clojure.set :as set]
   [v0_1_X.inputs :as inputs]
   [helpers :as helpers]))

;; CONFIG FUNCTIONS

;; You apply a strategy to source and target inputs to produce a return stream

(defn get-index-pairs
  "returns set of sets"
  [num-inputs]
  (set
   (filter
    #(not (nil? %))
    (for [x (range num-inputs) y (range num-inputs)]
      (when (not= x y)  #{x y})))))

(defn get-tree-config 
  "return-type is: long-only | short-only | ternary"
  ([min-depth max-depth num-inputs] (get-tree-config min-depth max-depth num-inputs "long-only"))
  ([min-depth max-depth num-inputs return-type]
   (let [bintern (if (contains? #{"long-only" "ternary"} return-type) return-type "long-only")]
   {:min-depth min-depth :max-depth max-depth :index-pairs (get-index-pairs num-inputs) :return-type bintern})))

;; MAKE TREE

(defn make-tree-recur
  "available-ind-sets is the set of total index sets minus (difference) node parent index sets"
  ([tree-config] (make-tree-recur (tree-config :index-pairs) tree-config 0))
  ([available-ind-sets tree-config depth]
   (let [ind-set (rand-nth (seq available-ind-sets))
         new-available-ind-sets (set/difference available-ind-sets #{ind-set})
         make-child #(if (or (empty? new-available-ind-sets) 
                          (and (>= depth (tree-config :min-depth))
                               (or (> (rand) 0.3) (>= depth (tree-config :max-depth)))))
                       (rand-nth (helpers/return-type->vec (get tree-config :return-type)))
                       (make-tree-recur new-available-ind-sets tree-config (inc depth)))]
     (as-> [] $
       (z/vector-zip $)
       (z/append-child $ ind-set)
       (z/append-child $ (make-child))
       (z/append-child $ (make-child))
       (z/node $)))))

(defn ameliorate-tree
  "This function only works on vector trees.
   Walk the tree. If two branches are identical, replace the first branch with boolean opposite of second branch"
  [tree]
  (w/postwalk
   #(if (and
         (= (type %) clojure.lang.PersistentVector)
         (= (nth % 1) (nth % 2)))
      ;; Make sure to only potentially inlude -1 if tree-config return-type is "ternary", if "long-only" values are only 0 and 1
      ;[(first %) (- (mod (+ (last %) 2) 3) 1) (last %)] ;; This makes [cond 1 1] -> [cond -1 1] with 1 -> -1, 0 -> 1, -1 -> 0 for middle leaf
      
      ;; This is easier for now...
      (last %)
      %)
   tree))

(defn make-tree
  ([tree-config]
   (-> tree-config
       (make-tree-recur)
       (ameliorate-tree))))

;; SOLVE TREE FUNCTIONS

(defn solve-cond [inputs input-indxs]
  (let [inputsVec (vec inputs)]
   (> (inputsVec (first input-indxs)) (inputsVec (last input-indxs)))))

(defn solve-tree
  "Solves tree for one 'moment in time'. inst-inputs (instance (or instant?) inputs) refers to the nth index of each input stream"
  [tree inst-inputs]
  (if (= (type tree) java.lang.Long)
    tree
    (solve-tree
     (if (solve-cond inst-inputs (first tree))
       (nth tree 1)
       (nth tree 2))
     inst-inputs)))

;; CODIFY INPUT DATA FUNCTIONS

(defn rand-caps-str [len]
  (apply str (take len (repeatedly #(char (+ (rand 26) 65))))))

(defn rand-suffix [input-str]
  (str input-str "-" (rand-caps-str 10)))

(defn get-stream-from-fn
  ([fn num-data-points]
   (mapv fn (range num-data-points))))

(defn zip-inception-streams [& streams]
  (loop [i 0 v (transient [])]
    (if (< i (count (first streams)))
      (recur (inc i) (conj! v (vec (for [stream streams] (stream i)))))
      (persistent! v))))

;; GET (AND POPULATE) STRATEGY FUNCTIONS

(defn get-stream-delta
  ([stream] (get-stream-delta stream (str (or (get (meta stream) :name) "no name") " delta")))
  ([stream name]
   (with-meta
     (into [0.0]
           (for [i (range (- (count stream) 1))]
             (- (stream (+ i 1)) (stream i))))
     {:name name})))

(defn get-streams-delta [streams]
  (for [stream streams]
    (get-stream-delta stream)))

(defn get-input-streams-util [input-config target-key]
  (for [inception-stream-config (get input-config target-key)]
    (with-meta
      (get-stream-from-fn (get inception-stream-config :fn) (get input-config :num-data-points))
      {:name (get inception-stream-config :name) :args (get inception-stream-config :args)})))

(defn get-input-streams [input-config]
  (let [inception-streams (get-input-streams-util input-config :inception-streams-config)
        intention-streams (get-input-streams-util input-config :intention-streams-config)]
    {:inception-streams inception-streams
     :intention-streams intention-streams
     :intention-streams-delta (get-streams-delta intention-streams)}))

(defn get-sieve-stream
  [name inception-streams strat-tree solve-tree-fn]
  (with-meta (vec 
              (for
               [inst-inputs
                (apply zip-inception-streams inception-streams)]
                  (solve-tree-fn strat-tree inst-inputs)))
    {:name name}))

(defn get-return-stream [sieve-stream intention-stream-delta]
  (loop [i 1 v (transient [0.0])]
    (if (< i (count sieve-stream))
      (recur (inc i) (conj! v (+ (v (- i 1)) (* (sieve-stream (- i 1)) (intention-stream-delta i)))))
      (persistent! v))))

(defn get-return-streams [sieve-stream intention-streams-delta]
  (for [intention-stream-delta intention-streams-delta]
    (with-meta (vec (get-return-stream sieve-stream intention-stream-delta)) {:name (str "return stream " (rand-caps-str 5))})))

(defn get-populated-strat-from-tree
  ([tree input-config] (get-populated-strat-from-tree tree input-config solve-tree))
  ([tree input-config solve-tree-fn]
   (let [name (rand-suffix "strat")
         input-streams (get-input-streams input-config)
         sieve-stream (get-sieve-stream (str name " sieve stream") (get input-streams :inception-streams) tree solve-tree-fn)
         return-streams (get-return-streams sieve-stream (get input-streams :intention-streams-delta))]
     {:name name :input-streams input-streams :tree tree :sieve-stream sieve-stream :return-streams return-streams})))

(defn get-populated-strat
  ([input-config tree-config] (get-populated-strat input-config tree-config make-tree solve-tree))
  ([input-config tree-config make-tree-fn solve-tree-fn]
   (let [tree (make-tree-fn tree-config)]
     (get-populated-strat-from-tree tree input-config solve-tree-fn))))

;; VISUALIZATION FORMATTING FUNCTION

(defn format-stream-for-view
  "returns a collection of view data (maps of form {:item <stream name> :x <x input angle> :y <stream solution at x>} )
   from the stream"
  [stream]
  (let [item  (or (get (meta stream) :name) "no name")]
    (loop [i 0 v (transient [])]
      (if (< i (count stream))
        (recur (inc i) (conj! v {:item item :x i :y (stream i)})) ;; view data structure
        (persistent! v)))))

(defn format-streams-for-view [streams]
  (for [stream streams] (format-stream-for-view stream)))

;; CREATE POPULATED STRATEGY AND VIEW PLOT

(defn get-strats-input-and-return-streams [input-config & strats]
  (let [input-streams (get-input-streams input-config)
        plot-streams (vec (into (get input-streams :inception-streams) (get input-streams :intention-streams)))]
    (loop [i 0 v plot-streams]
      (if (< i (count strats))
        (recur (inc i) (into v (get (nth strats i) :return-streams)))
        v))))

(defn get-plot-values [plot-streams]
  (flatten
   (map
    format-stream-for-view
    plot-streams)))

(defn generate-and-view-plot [values]
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

(defn plot-stream [stream]
  (generate-and-view-plot (format-stream-for-view stream)))

(defn plot-streams [streams]
  (generate-and-view-plot (format-streams-for-view streams)))

(defn plot-strats-and-inputs [input-config & strats]
  (generate-and-view-plot
   (get-plot-values
    (apply get-strats-input-and-return-streams input-config strats))))

(defn plot-strats [& strats]
  (generate-and-view-plot
   (get-plot-values
    (map :return-stream strats))))

(defn get-strats-info [strats]
  (println (map :fitness strats))
  (pp/pprint (map :tree strats)))

(comment
  (def input-config (inputs/get-sine-inputs-config 4 2 1000 10 0.1 0 100))
  (def tree-config (get-tree-config 2 6 (count (get input-config :inception-streams-config))))
  (def strat1 (get-populated-strat input-config tree-config))
  (def strat2 (get-populated-strat input-config tree-config))
  (def strat3 (get-populated-strat input-config tree-config))
  (def strat4 (get-populated-strat input-config tree-config))
  (plot-strats-and-inputs input-config strat1 strat2 strat3 strat4)
  )