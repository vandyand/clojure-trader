(ns v0_2_X.strindicator
  (:require [stats :as stats]
            [clojure.pprint :as pp]
            [clojure.walk :as w]
            [v0_1_X.strategy :as strat]
            [oz.core :as oz]))

(defn pos-or-zero [num] (if (pos? num) num 0))

(defn solve-strindy-for-inst-incep [strindy inception-streams]
  (if (contains? strindy :id)
    (let [stream-id (get strindy :id)
          target-inception-stream (get inception-streams stream-id)
          target-inception-stream-ind (pos-or-zero (- (- (count target-inception-stream) 1) (or (get strindy :shift) 0)))]
      (get-in target-inception-stream [target-inception-stream-ind (get strindy :key)]))
    (let [strind-fn (get-in strindy [:policy :fn])
          strind-inputs (get strindy :inputs)]
      (if (number? strind-fn) strind-fn
          (let [solution (apply strind-fn (mapv #(solve-strindy-for-inst-incep % inception-streams) strind-inputs))]
            (if (Double/isNaN solution) 0.0 solution))))))

(defn stream->rivulet [stream] (mapv - stream (cons (first stream) stream)))

(defn sieve->rivulet [sieve intention-rivulet]
  (if (not= 0 (count sieve)) (mapv * (cons (first sieve) sieve) intention-rivulet) [])
  )

(defn slippage-sieve->rivulet 
  ([s i-r] (slippage-sieve->rivulet s i-r 0))
  ([s i-r penalty]
   "new sieve->rivulet
   This penalizes opening and closing trades to simulate spread"
   (loop [v [0.0]]
     (if (< (count v) (count i-r))
       (let [ind  (dec (count v))
             prev-sval (s (if (= ind 0) 0 (dec ind)))
             sval (s ind)
             rval (i-r (inc ind))
             offset (if (not= prev-sval sval) penalty 0.0)
             res (+ offset (* sval rval))]
         (recur (conj v res)))
       v))))

(comment 
  (let [sieve [0      1       1      0       0      1      0        0      -1     -1     0      -1     1      1]
        riv [0.001 0.0004 -0.0008 -0.0001 0.0004 0.0002 -0.0012 -0.0003 0.0002 -0.0007 0.0009 0.0001 0.0003 -0.001]]
    (println (sieve->rivulet sieve riv))
    (slippage-sieve->rivulet sieve riv)))

(defn rivulet->beck [rivulet] 
  (reduce (fn [acc newVal] (conj acc (+ newVal (or (last acc) 0)))) [] rivulet))

;; TODO - make this performant? or get rid of it...
(defn get-streams-walker [streams]
  (mapv (fn [ind]
          (mapv (fn [vect]
                  (subvec vect 0 ind))
                streams))
        (range 1 (count (first streams)))))

(defn get-sum-of-all-streams [return-streams]
  (let [stream-length (count (get (first return-streams) :beck))
        sum-rivulet
        (vec (for [n (range stream-length)]
               (reduce + (for [return-stream return-streams] (get-in return-stream [:rivulet n])))))
        sum-beck
        (vec (for [n (range stream-length)]
               (reduce + (for [return-stream return-streams] (get-in return-stream [:beck n])))))]
    {:rivulet sum-rivulet :beck sum-beck}))

(defn get-sieve-stream [strindy inception-streams]
  (let [inception-streams-walker (get-streams-walker inception-streams)]
    (mapv #(solve-strindy-for-inst-incep strindy %) inception-streams-walker)))

(defn sieve->return [sieve-stream intention-streams]
  (let [intention-streams-rivulet 
        (for [intention-stream intention-streams]
          (stream->rivulet (map :c intention-stream)))
        return-streams (for [intention-rivulet intention-streams-rivulet]
                         (let [slippage (if (> 10 (-> intention-streams ffirst :o)) -0.000025 -0.0025)
                               return-rivulet (slippage-sieve->rivulet sieve-stream intention-rivulet slippage)]
                           {:rivulet return-rivulet
                            :beck (rivulet->beck return-rivulet)}))]
    (get-sum-of-all-streams return-streams)))

;;---------------------------------------;;---------------------------------------;;---------------------------------------;;---------------------------------------

(def strindy-funcs
  [
  ;;  {:type "sin" :fn (fn [& args] (Math/sin (first args)))}
  ;;  {:type "cos" :fn (fn [& args] (Math/cos (first args)))}
  ;;  {:type "tan" :fn (fn [& args] (Math/tan (first args)))}
  ;;  {:type "mlog" :fn (fn [& args] (Math/log (Math/abs (+ Math/E (first args)))))}
  ;;  {:type "pow" :fn (fn [& args] (let [arg1 (first args) arg2 (if (= 1 (count args)) (first args) (second args))]
  ;;                                  (Math/pow arg1 arg2)))}
  ;;  {:type "binary" :fn (fn [& args] (if (= 1 (count args)) 0 (if (> (first args) (second args)) 1 0)))}
   {:type "+" :fn (fn [& args] (apply + args))}
   {:type "-" :fn (fn [& args] (apply - args))}
   {:type "*" :fn (fn [& args] (apply * args))}
   {:type "/" :fn (fn [& args] (reduce (fn [acc newVal] (if (= 0.0 (double newVal)) 0.0 (/ acc newVal))) args))}
  ;;  {:type "max" :fn (fn [& args] (apply max args))}
  ;;  {:type "min" :fn (fn [& args] (apply min args))}
  ;;  {:type "mean" :fn (fn [& args] (stats/mean args))}
  ;;  {:type "stdev" :fn (fn [& args] (stats/stdev args))}
   ])

(defn make-input [inception-ids]
  {:id (rand-nth inception-ids) :key (rand-nth '(:v :o :h :l :c)) :shift (first (random-sample 0.1 (range)))})

(defn make-strindy-recur
  ([config] (make-strindy-recur config 0))
  ([config current-depth]
   (if (and (>= current-depth (get config :min-depth)) (or (> (rand) 0.5) (= current-depth (get config :max-depth))))
     (cond (< (rand) 0.9) (make-input (get config :inception-ids))
           :else (let [r (rand)] {:policy {:type "rand" :value r :fn (constantly r)}}))
     (let [parent-node? (= current-depth 0)
           max-children (get config :max-children)
           num-inputs (or (first (random-sample 0.4 (range (if parent-node? 2 1) max-children))) max-children)
           tree-node? (or (and parent-node? (contains? #{"long-only" "short-only" "ternary"} (get config :return-type))) 
                          (and (>= num-inputs 2) (< (rand) 0.1)))
           strat-tree (when tree-node? (strat/make-tree (strat/get-tree-config 2 5 num-inputs (get config :return-type))))
           inputs (vec (repeatedly num-inputs #(make-strindy-recur config (inc current-depth))))
           func (if tree-node?
                  {:type "strategy" :tree strat-tree :fn (fn [& args] (strat/solve-tree strat-tree args))}
                  (rand-nth strindy-funcs))]
       {:policy func
        :inputs inputs}))))

(defn ameliorate-strindy [strindy]
  (w/postwalk (fn [form]
                (if (and (map? form)
                         (some #(= % :inputs) (keys form)))
                  (let [policy-type (get-in form [:policy :type])
                        inputs (get form :inputs)
                        name-match #(= % policy-type)]
                    (cond (and (some name-match ["sin" "cos" "tan" "mlog"])
                               (> (count inputs) 1))
                          (assoc form :inputs (vector (rand-nth inputs)))
                          (and (some name-match ["+" "*" "max" "min" "mean"])
                               (= (count inputs) 1))
                          (first inputs)
                          (and (some name-match ["pow" "binary"])
                               (> (count inputs) 2))
                          (assoc form :inputs (let [shuffled (shuffle inputs)] (vector (first shuffled) (second shuffled))))
                          :else form))
                  form))
              strindy))

(defn ameliorate-strindy-recur [strindy]
  (let [new-strindy (ameliorate-strindy strindy)]
    (if (= strindy new-strindy) strindy (ameliorate-strindy-recur new-strindy))))

(defn make-strindy [config]
  (-> config (make-strindy-recur) (ameliorate-strindy-recur)))

(defn print-strindy [strindy]
  (pp/pprint
   (w/postwalk
    (fn [form]
      (if (and (map? form) (some #(= % :policy) (keys form)))
        {:type (get-in form [:policy :type]) :inputs (form :inputs)}
        form))
    strindy)))
