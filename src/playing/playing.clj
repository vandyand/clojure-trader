(ns playing.playing
  (:require [clojure.pprint :as pp]))

(defmacro thing [arg1 arg2]
  `[~arg1 ~arg2])

(macroexpand (thing 2 3))
(macroexpand-1 (thing 2 3))

(thing 2 4)

(defmacro infix [form]
  (list (second form) (first form) (nth form 2)))

(infix (2 + 9))

(macroexpand (infix (2 + 4)))

(= '(1 2 3) `(1 2 ~(infix (2 + 1))))

(defn funnc [i]
  (fn [x] (* i x)))

((funnc 3) 4)

(defmacro func [& args]
  `(* ~(for [arg args] arg)))

(func 3 4)

(macroexpand (func 3))

(map (func 3) [2 3 4])

(defmacro thing [& args]
  (apply + args))

(thing 2 3)

(defmacro func-gen []
  `(defn ~(symbol "nameee") [arg1] {:arg1 arg1}))

(pp/pprint (macroexpand-1 (func-gen)))
