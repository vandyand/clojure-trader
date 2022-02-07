(ns incubator.strategy
  (:require
  ;;  [clojure.spec.alpha :as s]
  ;;  [clojure.spec.gen.alpha :as sgen]
  ;;  [clojure.test.check.generators :as gen]
   [clojure.string :as cs]
   [clojure.walk :as w]
   [oz.core :as oz]
   [clojure.set :as set]
   [incubator.sine_waves :as sw]))

;; START SERVER FOR VISUALIZATION

(oz/start-server! 10667)


;; CONFIG SETTINGS


(defn get-input-config [num-input-streams num-data-points amp freq v-shift h-shift]
  {:num-input-streams num-input-streams
   :num-data-points num-data-points
   :amp amp
   :freq freq
   :v-shift v-shift
   :h-shift h-shift})

(defn get-tree-config [min-depth max-depth index-pairs]
  {:min-depth min-depth :max-depth max-depth :index-pairs index-pairs})

(defn get-index-pairs [num-inputs]
  (set (filter
        #(not= (first %) (last %))
        (for [x (range num-inputs) y (range num-inputs)] [x y]))))


;; MAKE TREE


(defn isArrayMap? [testee] (= (type testee) clojure.lang.PersistentArrayMap))
(defn isLong? [testee] (= (type testee) java.lang.Long))

(defn make-raw-tree-recur
  ([tree-config] (make-raw-tree-recur tree-config {} 0 #{}))
  ([config tree depth index-pairs-used]
   (if (and (>= depth (config :min-depth)) (or (> (rand) 0.5) (= depth (config :max-depth))))
     (rand-nth [1 0])
     (let [index-pair (rand-nth (vec (set/difference (config :index-pairs) index-pairs-used)))
           new-branch #(make-raw-tree-recur config tree (inc depth) (set/union #{index-pair} index-pairs-used))]
       {:input-indxs index-pair
        :branchA (new-branch)
        :branchB (new-branch)}))))

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
  ([] (make-tree (get-tree-config 2 6 (get-index-pairs 4))))
  ([tree-config] (ameliorate-tree (make-raw-tree-recur tree-config))))

(defn print-tree [tree]
  (print (cs/replace (str tree) ":b" "\n:b")))

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


;; CODIFY INPUT DATA FUNCTIONS


(defn rand-caps-str [len]
  (apply str (take len (repeatedly #(char (+ (rand 26) 65))))))

(defn rand-suffix [input-str]
  (str input-str "-" (rand-caps-str 10)))

(defn scaled-rand-dbl
  "returns random double between min (inclusive) and max (exclusive)"
  [min max]
  (-> (- max min) (rand) (+ min)))

(defn get-stream-config [input-config]
  (let [rand-amp (scaled-rand-dbl 0 (input-config :amp))
        rand-freq (scaled-rand-dbl 0 (input-config :freq))
        rand-h-shift (scaled-rand-dbl 0 (input-config :h-shift))
        rand-v-shift (scaled-rand-dbl 0 (input-config :v-shift))
        args {:amp rand-amp :freq rand-freq :h-shift rand-h-shift :v-shift rand-v-shift}
        name (sw/get-sine-fn-name args)]
    {:name name
     :args args
     :fn (fn [x]
           (-> x
               (* rand-freq)
               (- rand-h-shift)
               (Math/sin)
               (* rand-amp)
               (+ rand-v-shift)))}))

(defn get-random-sine-stream
  ([config]
   (let [stream-config (get-stream-config config)]
     (with-meta
       (mapv
        (stream-config :fn)
        (range (config :num-data-points)))
       {:name (stream-config :name) :args (stream-config :args)}))))

(defn zip-input-streams [& streams]
  (loop [i 0 v (transient [])]
    (if (< i (count (first streams)))
      (recur (inc i) (conj! v (vec (for [stream streams] (stream i)))))
      (persistent! v))))


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
  (let [name (rand-suffix "strat")
        sieve-stream (get-sieve-stream (str name " sieve stream") (input-and-target-streams :input-streams) tree solve-tree-fn)
        return-stream (get-return-stream (str name " return stream") sieve-stream (input-and-target-streams :target-stream-delta))]
    {:name name :tree tree :sieve-stream sieve-stream :return-stream return-stream}))

(defn get-populated-strat
  ([input-and-target-streams tree-config] (get-populated-strat input-and-target-streams tree-config make-tree solve-tree))
  ([input-and-target-streams tree-config make-tree-fn solve-tree-fn]
   (let [tree (make-tree-fn tree-config)]
     (get-populated-strat-from-tree tree input-and-target-streams solve-tree-fn))))


;; GET INPUT STREAMS AND TARGET DELTA STREAM FUNCTIONS


(defn get-input-streams [input-config]
  (repeatedly (input-config :num-input-streams) #(get-random-sine-stream input-config)))

(defn get-stream-delta
  ([stream] (get-stream-delta stream "stream delta"))
  ([stream name]
   (with-meta
     (into [0.0]
           (for [i (range (- (count stream) 1))]
             (- (stream (+ i 1)) (stream i))))
     {:name name})))

(defn get-input-and-target-streams [input-config]
  (let [input-streams (get-input-streams input-config)
        target-stream (with-meta (rand-nth input-streams) {:name "target stream"})]
    {:input-streams input-streams :target-stream target-stream :target-stream-delta (get-stream-delta target-stream "target")}))



;; VISUALIZATION FORMATTING FUNCTION


(defn format-stream-for-view
  "returns a collection of view data (maps) of form {:item <stream name> :x <x input angle> :y <stream solution at x>} from the stream"
  [stream]
  (let [item  ((meta stream) :name)]
    (loop [i 0 v (transient [])]
      (if (< i (count stream))
        (recur (inc i) (conj! v {:item item :x i :y (stream i)}))
        (persistent! v)))))


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

(defn plot-strats-with-input-target-streams [input-and-target-streams & strats]
  (generate-and-view-plot
   (get-plot-values
    (apply get-plot-streams input-and-target-streams strats))))

(defn plot-strats [& strats]
  (generate-and-view-plot
   (get-plot-values
    (map :return-stream strats))))

(time
 (do
   (def inputs-config (get-input-config 4 100 10 0.1 0 100))
   (def tree-config (get-tree-config 2 6 (get-index-pairs (inputs-config :num-input-streams))))
   (def input-and-target-streams (get-input-and-target-streams inputs-config))
   (def strat1 (get-populated-strat input-and-target-streams tree-config))
   (def strat2 (get-populated-strat input-and-target-streams tree-config))
   (def strat3 (get-populated-strat input-and-target-streams tree-config))
   (def strat4 (get-populated-strat input-and-target-streams tree-config))
   (plot-strats-with-input-target-streams input-and-target-streams strat1 strat2 strat3 strat4)))

