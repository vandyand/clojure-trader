(ns v0_2_X.strindicator
  (:require [stats :as stats]
            [clojure.pprint :as pp]
            [clojure.walk :as w]
            [v0_1_X.strategy :as strat]
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
    (let [strind-fn (get-in strindy [:policy :fn])
          strind-inputs (get strindy :inputs)]
      (if (number? strind-fn) strind-fn
          (let [solution (apply strind-fn (mapv #(solve-strindy-for-inst-incep % inception-streams) strind-inputs))]
            (if (Double/isNaN solution) 0.0 solution))))))

(defn stream->rivulet [stream] (mapv - stream (cons (first stream) stream)))

(defn sieve->rivulet [sieve intention-rivulet] 
  (mapv * (conj sieve 0) intention-rivulet))

(defn rivulet->beck [rivulet] (reduce (fn [acc newVal] (conj acc (+ newVal (or (last acc) 0)))) [] rivulet))

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
  (let [intention-streams-rivulet (for [intention-stream intention-streams] (stream->rivulet intention-stream))
        return-streams (for [intention-rivulet intention-streams-rivulet]
                         (let [return-rivulet (sieve->rivulet sieve-stream intention-rivulet)]
                           {:rivulet return-rivulet
                            :beck (rivulet->beck return-rivulet)}))]
    (get-sum-of-all-streams return-streams)))

;;---------------------------------------;;---------------------------------------;;---------------------------------------;;---------------------------------------

(def strindy-funcs
  [{:type "sin" :fn (fn [& args] (Math/sin (first args)))}
   {:type "cos" :fn (fn [& args] (Math/cos (first args)))}
   {:type "tan" :fn (fn [& args] (Math/tan (first args)))}
  ;;  {:type "mlog" :fn (fn [& args] (Math/log (Math/abs (+ Math/E (first args)))))}
  ;;  {:type "pow" :fn (fn [& args] (let [arg1 (first args) arg2 (if (= 1 (count args)) (first args) (second args))]
  ;;                                  (Math/pow arg1 arg2)))}
  ;;  {:type "binary" :fn (fn [& args] (if (= 1 (count args)) 0 (if (> (first args) (second args)) 1 0)))}
   {:type "+" :fn (fn [& args] (apply + args))}
   {:type "-" :fn (fn [& args] (apply - args))}
  ;;  {:type "*" :fn (fn [& args] (apply * args))}
  ;;  {:type "/" :fn (fn [& args] (reduce (fn [acc newVal] (if (= 0.0 (double newVal)) 0.0 (/ acc newVal))) args))}
  ;;  {:type "max" :fn (fn [& args] (apply max args))}
  ;;  {:type "min" :fn (fn [& args] (apply min args))}
  ;;  {:type "mean" :fn (fn [& args] (stats/mean args))}
  ;;  {:type "stdev" :fn (fn [& args] (stats/stdev args))}
   ])

(defn make-input [inception-ids]
  {:id (rand-nth inception-ids) :shift (first (random-sample 0.5 (range)))})

(defn make-strindy-recur
  ([config] (make-strindy-recur config 0))
  ([config current-depth]
   (if (and (>= current-depth (get config :min-depth)) (or (> (rand) 0.5) (= current-depth (get config :max-depth))))
     (cond (< (rand) 0.9) (make-input (get config :inception-ids))
           :else (let [r (rand)] {:policy {:type "rand" :value r :fn (constantly r)}}))
     (let [parent-node? (= current-depth 0)
           max-children (get config :max-children)
           num-inputs (or (first (random-sample 0.4 (range (if parent-node? 2 1) max-children))) max-children)
           tree-node? (or (and parent-node? (= (get config :return-type) "binary")) (and (>= num-inputs 2) (< (rand) 0.1)))
           strat-tree (when tree-node? (strat/make-tree (strat/get-tree-config 2 5 num-inputs)))
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
