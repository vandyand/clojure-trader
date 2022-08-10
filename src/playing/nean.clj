(ns playing.nean
  (:require
   [uncomplicate.neanderthal.core :as nean]
   [uncomplicate.neanderthal.native :as nat]
   [uncomplicate.fluokitten.core :refer [fmap fmap! fold foldmap]]
   [criterium.core :refer [quick-bench with-progress-reporting]]
   [midje.sweet :as mj]
   [config :as config]
   [v0_2_X.streams :as streams]))

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
      rand-comp (fn ^double [^double x ^double y] )
      a (nat/dv (-> 1000 range))
      b (nat/dv (->> #(rand) repeatedly (take 1000) (map #(* % 1000))))]
   (fmap! grt a b))


(defn vec-add [xs ys] (mapv + xs ys))
(defn vec-sub [xs ys] (mapv - xs ys))
(defn vec-mult [xs ys] (mapv * xs ys))
(defn vec-div [xs ys] (mapv / xs ys))
(defn vec-grt [xs ys] (mapv (fn ^double [^double x ^double y] (->> (- x y) (* -1E10) Math/exp (+ 1) (/ 1)))xs ys))

(let [a [1 2 3 4]
      b [5 6 7 8]
      c [100 101 102 103]
      d [20 40 60 80]]
  (->> a (mapv + b) (mapv - d) (mapv / c) (mapv + c) (mapv double) (vec-grt c)))


(def backtest-config (config/get-backtest-config-util
                      ["EUR_USD" "both"]
                      "ternary" 1 2 3 1050 "M15"))

(def streams (streams/fetch-formatted-streams backtest-config))

(def open (->> streams :inception-streams first (mapv :o)))
(def close (->> streams :inception-streams first (mapv :c)))

(let [o (nat/dv open)
      c (nat/dv close)
      grt (fn ^double [^double x ^double y] (->> (- x y) (* -1E10) Math/exp (+ 1) (/ 1)))
      func (fn ^double [^double x ^double y] (- x y))
]
  (fmap! func o c))



















