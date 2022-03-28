(ns v0_3_X.gauntlet
  (:require
   [edn]))


(def hystrindies (edn/get-hystrindies-from-file))

(defn get-overlap-ind [old new]
  (loop [i 0]
    (cond
      (>= i (count new)) -1
      (let [sub-new (subvec new 0 (- (count new) i))
            sub-old (subvec old (- (count old) (count sub-new)))]
        (= sub-old sub-new))
      i
      :else (recur (inc i)))))

(defn get-fore-series [new overlap-ind]
  (subvec new (- (count new) overlap-ind)))

(comment 
 (let [new [9 10 11 12 13 14]
      old [2 3 4 5 6 7 8 9 10]]
  (get-fore-series new (get-overlap-ind old new))))