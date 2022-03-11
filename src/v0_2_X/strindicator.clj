(ns v0_2_X.strindicator
  (:require [stats :as stats]
            [clojure.pprint :as pp]
            [v0_1_X.incubator.strategy :as strat]
            [oz.core :as oz]))

(def streams-db [(vec (range 100))
                 [1.13104 1.12975 1.12947 1.12943 1.13064 1.13053 1.1306 1.13118 1.13106 1.13188 1.13174 1.13192 1.13174 1.13219 1.13126 1.13461 1.13462 1.13482 1.1346 1.13408 1.13558 1.13219 1.13548 1.13626 1.13588 1.13554 1.13596 1.13582 1.1358 1.13578 1.13553 1.13573 1.13521 1.13472 1.1346 1.1348 1.13539 1.13636 1.13754 1.13898 1.13774 1.13806 1.13852 1.13656 1.1363 1.13653 1.13654 1.13808 1.13744 1.1377 1.13905 1.1382 1.13736 1.1376 1.13728 1.13796 1.13818 1.13828 1.13363 1.13422 1.13566 1.13604 1.13752 1.13584 1.13614 1.13755 1.13656 1.13778 1.13594 1.13594 1.13694 1.13628 1.13593 1.13628 1.13642 1.13601 1.13625 1.13614 1.13637 1.13598 1.13682 1.1367 1.13675 1.13638 1.1366 1.13709 1.137 1.13758 1.1371 1.1361 1.13626 1.13602 1.13491 1.13482 1.13411 1.13259 1.13224 1.13302 1.13312 1.13249]])

(defn pos-or-zero [num] (if (pos? num) num 0))

(defn solve-strindy-for-inst-incep [strindy inception-streams]
  (if (contains? strindy :id)
    (let [stream-id (get strindy :id)
          target-inception-stream (get inception-streams stream-id)
          target-inception-stream-ind (pos-or-zero (- (- (count target-inception-stream) 1) (or (get strindy :shift) 0)))]
      (get target-inception-stream target-inception-stream-ind))
    (let [strind-fn (get strindy :fn)
          strind-inputs (get strindy :inputs)]
      (if (number? strind-fn) strind-fn
          (let [solution (apply strind-fn (mapv #(solve-strindy-for-inst-incep % inception-streams) strind-inputs))]
            (if (Double/isNaN solution) 0.0 solution))))))

(defn get-stream-deltas [stream] (mapv - stream (cons (first stream) stream)))

(defn get-return-deltas [sieve intention-deltas] (map * (cons (first sieve) sieve) intention-deltas))

(defn get-stream-from-deltas [deltas] (reduce (fn [acc newVal] (conj acc (+ newVal (or (last acc) 0)))) [] deltas))

(defn get-streams-by-indexes [streams inds] (vec (for [ind inds] (get streams ind))))

;; TODO - make this performant? or get rid of it...
(defn get-streams-walker [streams]
  (mapv (fn [ind]
          (mapv (fn [vect]
                  (subvec vect 0 ind))
                streams))
        (range 1 (count (first streams)))))

(defn get-streams-sum [streams]
  (for [n (range (count (first streams)))]
    (apply + (for [stream streams] (get stream n)))))

(defn get-sieve-stream [strindy inception-streams]
  (let [inception-streams-walker (get-streams-walker inception-streams)]
    (mapv #(solve-strindy-for-inst-incep strindy %) inception-streams-walker)))

(defn get-return-streams-from-sieve [sieve-stream intention-streams]
  (let [return-streams (let [intention-streams-delta (for [intention-stream intention-streams] (get-stream-deltas intention-stream))]
         (for [intention-stream-delta intention-streams-delta]
           (let [return-deltas (get-return-deltas sieve-stream intention-stream-delta)]
             (get-stream-from-deltas return-deltas))))]
    (into return-streams (vector (vec (get-streams-sum return-streams))))))

;;---------------------------------------;;---------------------------------------;;---------------------------------------;;---------------------------------------

(def one-arg-funcs (list
                    (with-meta #(Math/sin %) {:name "sin"})
                    (with-meta #(Math/cos %) {:name "cos"})
                    (with-meta #(Math/tan %) {:name "tan"})
                    (with-meta #(Math/log (Math/abs (+ Math/E %))) {:name "modified log"})))

(def many-arg-funcs
  [(with-meta (fn [& args] (apply + args)) {:name "+"})
   (with-meta (fn [& args] (apply - args)) {:name "-"})
   (with-meta (fn [& args] (apply * args)) {:name "*"})
   (with-meta (fn [& args] (reduce (fn [acc newVal] (if (= 0.0 (double newVal)) 0.0 (/ acc newVal))) args)) {:name "/"})
   (with-meta (fn [& args] (apply max args)) {:name "max"})
   (with-meta (fn [& args] (apply min args)) {:name "min"})
   (with-meta (fn [& args] (stats/mean args)) {:name "mean"})
   (with-meta (fn [& args] (stats/stdev args)) {:name "stdev"})])

(def two-arg-funcs
  (into many-arg-funcs
        [(with-meta #(Math/pow %1 %2) {:name "pow"})
         (with-meta #(if (> %1 %2) 1 0) {:name "binary"})]))

(defn make-strindy-recur
  ([config] (make-strindy-recur config 0))
  ([config current-depth]
   (if (and (>= current-depth (get config :min-depth)) (or (> (rand) 0.5) (= current-depth (get config :max-depth))))
     (cond (< (rand) 0.75) {:id (rand-nth (get config :inception-ids)) :shift (first (random-sample 0.5 (range)))}
           :else {:fn-name "rand constant" :fn (rand) :inputs []})
     (let [parent-node? (= current-depth 0)
           max-children (get config :max-children)
           new-depth (inc current-depth)
           num-inputs (or (first (random-sample 0.4 (range (if parent-node? 2 1) max-children))) max-children)
           tree-node? (or (and parent-node? (= (get config :return-type) "binary")) (and (>= num-inputs 2) (< (rand) 0.1)))
           strat-tree (when tree-node? (strat/make-tree (strat/get-tree-config 0 5 num-inputs)))
           inputs (vec (repeatedly num-inputs #(make-strindy-recur config new-depth)))
           func (cond
                  tree-node? (with-meta (fn [& args] (strat/solve-tree strat-tree args)) {:name (str "binary tree with " num-inputs " inputs")})
                  (= num-inputs 1) (rand-nth one-arg-funcs)
                  (= num-inputs 2) (rand-nth two-arg-funcs)
                  (> num-inputs 2) (rand-nth many-arg-funcs))]
       {:fn-name (get (meta func) :name)
        :fn func
        :inputs inputs}))))

;;---------------------------------------;;---------------------------------------;;---------------------------------------;;---------------------------------------

(defn get-strindy-config [min-depth max-depth max-children inception-ids intention-ids]
  {:min-depth min-depth :max-depth max-depth :max-children max-children :inception-ids inception-ids :intention-ids intention-ids})

(def strindy-config (get-strindy-config 5 6 10 [0 1] [1]))

;;---------------------------------------;;---------------------------------------;;---------------------------------------;;---------------------------------------

;; (def strindy (make-strindy-recur strindy-config))
;; ;; (pp/pprint strindy)
;; (def sieve-stream (get-sieve-stream strindy strindy-config))
;; (def return-streams (get-return-streams-from-sieve sieve-stream strindy-config))

;; ;; (strat/plot-stream  (with-meta (vec (for [price (streams-db 1)] (- price (first (streams-db 1))))) {:name "eurusd zeroed"}))
;; (strat/plot-stream  (first return-streams))
