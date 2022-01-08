(ns strategies
  (:require
   [oz.core :as oz]
   [clojure.spec.alpha :as s]
   [clojure.spec.gen.alpha :as gen]))

(defn generate-gt-strategy [] (fn [inputs] (> (nth inputs 0) (nth inputs 1))))