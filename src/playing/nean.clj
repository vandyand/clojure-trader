(ns playing.nean
  (:require
   [uncomplicate.neanderthal.core :as nean]
   [uncomplicate.neanderthal.native :as nat]
   [uncomplicate.fluokitten.core :refer [fmap fmap! fold foldmap]]
   [criterium.core :refer [quick-bench with-progress-reporting]]
   [midje.sweet :as mj]
   [config :as config]
   [v0_2_X.streams :as streams]
   [v0_2_X.plot :as plot]))

(time
 (do
   (def x (apply nat/dv (-> 1000 range)))
   (def y (apply nat/dv (->> 1000 range (map #(* % 10)))))
   (nean/xpy x y)))

(time
 (do
   (def x (-> 1000 range))
   (def y (->> 1000 range (map #(* % 10))))
   (mapv + x y)))


;;---------------------------------------------------------------------------------------------------


(def x (apply nat/dv (-> 100000 range)))
(def y (apply nat/dv (->> 100000 range (map #(* % 10)))))
(with-progress-reporting (quick-bench (nean/xpy x y)))

(def x (-> 100000 range))
(def y (->> 100000 range (map #(* % 10))))
(with-progress-reporting (quick-bench (mapv + x y)))


;;---------------------------------------------------------------------------------------------------


(let [primitive-inc (fn ^double [^double x] (inc x))
      primitive-add2 (fn ^double [^double x ^double y] (+ x y))
      primitive-add3 (fn ^double [^double x ^double y ^double z] (+ x y z))
      primitive-multiply (fn ^double [^double x ^double y] (* x y))
      a (nat/dge 2 3 (range 6))
      b (nat/dge 2 3 (range 0 60 10))
      c (nat/dge 2 3 (range 0 600 100))]
  (mj/fact
   "You can change individual entries of any structure with fmap!. You can also
accumulate values with fold, or fold the entries."
   (fmap! primitive-inc a) mj/=> (nat/dge 2 3 (range 1 7))
   a mj/=> (nat/dge 2 3 (range 1 7))
   (fmap! primitive-add3 a b c) mj/=> (nat/dge 2 3 [1 112 223 334 445 556])
   a mj/=> (nat/dge 2 3 [1 112 223 334 445 556])
   (fold primitive-add2 0.0 b c) mj/=> 1650.0
   (fold c) mj/=> 1500.0
   (fold primitive-multiply 1.0 a) mj/=> 2.06397368128E12))

;;---------------------------------------------------------------------------------------------------

(let [bin (fn ^double [^double x ^double y] ((comp #(+ 0.5 %) #(/ % 2) #(Math/tanh (* 1000 %)) -) x y))
      grt (fn ^double [^double x ^double y] (->> (- x y) (* -1E10) Math/exp (+ 1) (/ 1)))
      func (fn ^double [^double x ^double y] (- x y))
      rand-comp (fn ^double [^double x ^double y])
      a (nat/dv (-> 1000 range))
      b (nat/dv (->> #(rand) repeatedly (take 1000) (map #(* % 1000))))]
  (fmap! grt a b))


(defn vec-add [xs ys] (mapv + xs ys))
(defn vec-sub [xs ys] (mapv - xs ys))
(defn vec-mult [xs ys] (mapv * xs ys))
(defn vec-div [xs ys] (mapv / xs ys))
(defn vec-grt [xs ys] (mapv (fn ^double [^double x ^double y] (->> (- x y) (* -1E10) Math/exp (+ 1) (/ 1))) xs ys))

(let [a [1 2 3 4]
      b [5 6 7 8]
      c [100 101 102 103]
      d [20 40 60 80]]
  (->> a (mapv + b) (mapv - d) (mapv / c) (mapv + c) (mapv double) (vec-grt c)))

;;---------------------------------------------------------------------------------------------------


(def backtest-config (config/get-backtest-config-util
                      ["EUR_USD" "both"]
                      "ternary" 1 2 3 5000 "M15"))

(def streams (streams/fetch-formatted-streams backtest-config))

(defn get-stream-by-key [streams ohlc-key]
  (->> streams :inception-streams first (mapv ohlc-key)))



(def open (get-stream-by-key streams :o))
(def high (get-stream-by-key streams :h))
(def low (get-stream-by-key streams :l))
(def close (get-stream-by-key streams :c))

(def shift1 1)
(def shift2 100)
(def shift3 20)
(def shift4 50)

(def in1-1 (subvec open (- (count open) (int (* 4/5 (count open))) shift1) (- (count open) shift1)))
(def in1 (subvec open (- (count open) (int (* 4/5 (count open))) 0) (- (count open) 0)))
(def in2 (subvec close (- (count close) (int (* 4/5 (count close))) shift2) (- (count close) shift2)))
(def in3 (subvec high (- (count high) (int (* 4/5 (count high))) shift3) (- (count high) shift3)))
(def in4 (subvec low (- (count low) (int (* 4/5 (count low))) shift4) (- (count low) shift4)))

(def nean-add (fn [& args] (apply + args)))
(def nean-sub (fn [& args] (apply - args)))
(def nean-mult (fn [& args] (apply * args)))
(def nean-grt (fn [x y] (->> (- x y) (* -1E10) Math/exp (+ 1) (/ 1))))

(def bool-and (fn [x y] (* x y)))
(def bool-not (fn [x] (-> x (+ 1) (mod 2))))
;; (def bool-or (fn [x y] (-> x (+ y) )))

(def zeroes (nean/zero (nat/fv open)))

(def o (nat/fv open))
(def h (nat/fv high))
(def l (nat/fv low))
(def c (nat/fv close))


(def i1-1 (nat/fv in1-1))
(def i1 (nat/fv in1))
(def i2 (nat/fv in2))
(def i3 (nat/fv in3))
(def i4 (nat/fv in4))


(time (take 10 (seq (fmap nean-grt (nean/axpy -1.0 i2 i1 i3) (nean/axpy -1.0 i3 i4 1.001 i2)))))

;; (def open-deltas (map - in1 in1-1))

(take 10 (seq (fmap nean-grt (nean/axpy -1.0 i2 i1 i3) (nean/axpy -1.0 i3 i4 1.001 i2))))


(time (fmap (fn [val prev-val] (- val prev-val)) i1 i1-1))

(defn stream->rivulet [stream] (mapv - stream (cons (first stream) stream)))
(defn rivulet->stream [rivulet] (vec (reductions + rivulet))) 
(defn rivulet->stream2 [rivulet] (reduce (fn [acc newVal] (conj acc (+ newVal (or (last acc) 0)))) [] rivulet))

(def open-deltas (stream->rivulet open))

(def return-rivulet (seq (fmap nean-mult open-deltas (fmap nean-grt (nean/axpy -1.0 i2 i1 i3) (nean/axpy -1.0 i3 i4 1.01 i2)))))

(with-progress-reporting (quick-bench (rivulet->stream return-rivulet)))
(with-progress-reporting (quick-bench (rivulet->stream2 return-rivulet)))

(def return-stream (rivulet->stream return-rivulet))

(plot/plot-streams [return-stream (plot/zero-stream open)])

;;---------------------------------------------------------------------------------------------------

;; ;; Doing it recursively... NOT!

;; (def o (nat/fv open))
;; (def h (nat/fv high))
;; (def l (nat/fv low))
;; (def c (nat/fv close))

;; (def thing1 (fmap nean-grt o c))

;; (def tree
;;   {:f nean-grt
;;    :ins [{:f nean-add :ins [o c]}
;;          {:f nean-add :ins [h l]}]})

;; (def tree
;;   {:f nean-grt :ins [o c]})

;; (defn solver-recur [tree]
;;   ;; tree is always a map 
;;   ;; if at least one input tree is undefined (unsolved) (if it's not an fv but a map)
;;   ;; define (solve) the input tree
;;   ;; else, define (solve) the tree

;;   (println "tree: " tree)

;;   (for [input (:ins tree)]
;;     (do
;;       (println "input: " input)
;;       (when (map? input)
;;         (solver-recur input))))
;;   (println "applying... " tree)
;;   (apply fmap (:f tree) (:ins tree)))


;; (def thing2 (solver-recur tree))



;; ---------------------------------------------------------------------------------------------------


;; (def backtest-config (config/get-backtest-config-util
;;                       ["EUR_USD" "both"]
;;                       "ternary" 1 2 3 5000 "M15"))

;; (def streams (streams/fetch-formatted-streams backtest-config))

;; (defn get-stream-by-key [streams ohlc-key]
;;   (->> streams :inception-streams first (mapv ohlc-key)))



;; (def open (get-stream-by-key streams :o))
;; (def high (get-stream-by-key streams :h))
;; (def low (get-stream-by-key streams :l))
;; (def close (get-stream-by-key streams :c))

;; (def nean-add (fn [& args] (apply + args)))
;; (def nean-sub (fn [& args] (apply - args)))
;; (def nean-grt (fn ^double [x y] (->> (- x y) (* -1E10) Math/exp (+ 1) (/ 1))))

;; (def bool-and (fn [x y] (* x y)))
;; (def bool-not (fn [x] (-> x (+ 1) (mod 2))))
;; ;; (def bool-or (fn [x y] (-> x (+ y) )))

;; (def zeroes (nean/zero (nat/fv open)))

;; (def o (nat/fv open))
;; (def h (nat/fv high))
;; (def l (nat/fv low))
;; (def c (nat/fv close))

;; (defn abc [x]
;;   (take 10 (seq x)))

;; (abc (fmap (comp bool-not nean-grt) o c))

;; (abc (fmap bool-not (fmap nean-grt o c)))


;; (defn comp-add [ind1 ind2]
;;   (fn [inputs] (+ (nth inputs ind1) (nth inputs ind2))))

;; (defn comp-sub [ind1 ind2]
;;   (fn [inputs] (- (nth inputs ind1) (nth inputs ind2))))

;; (defn compf [f ind1 ind2]
;;   (fn [inputs] (f (nth inputs ind1) (nth inputs ind2))))

;; (map (fn [inputs] (- (nth inputs 0) (nth inputs 1))) [[o h l c]])

;; ;;---------------------------------------------------------------------------------------------------

;; (def stuff {:a [1 2 3 4]
;;            :b [10 20 30 40]
;;            :c [10 9 8 7]})

;; (map identity stuff)

;; (map + (stuff :a) (stuff :b))

