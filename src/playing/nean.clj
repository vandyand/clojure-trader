(ns playing.nean
  (:require
   [uncomplicate.neanderthal.core :as nean]
   [uncomplicate.neanderthal.native :as nat]
   [uncomplicate.fluokitten.core :refer [fmap fmap! fold foldmap]]
   [criterium.core :refer [quick-bench with-progress-reporting]]
   [midje.sweet :as mj]))

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


(let [grt (fn ^double [^double x ^double y] (> x y))
      a (nat/dv (-> 1000 range))
      b (nat/dv (->> #(rand) repeatedly (take 1000) (map #(* % 1000))))]
   (fmap! grt a b))




