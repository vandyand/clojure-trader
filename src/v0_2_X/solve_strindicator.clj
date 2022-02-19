(ns v0_2_X.solve_strindicator
  (:require [stats :as stats]
            [clojure.pprint :as pp]
            [v0_2_X.build_strindicator :as bstgr]))

(def num-data-points 10)

(def strindicator {:inputs [{:id 0}
                           {:inputs [{:id 0 :shift 0}]
                            :fn #(+ 1 %)}
                           {:inputs [{:id 0}
                                     {:inputs [{:id 0 :shift 0}]
                                      :fn #(+ % 1)}]
                            :fn #(+ 1 %1 %2)}]
                  :fn (fn [& args] (reduce + args))})

(def subscription-streams [{:id 0 :stream (vec (range num-data-points))}])

(defn get-subscription-stream-val [subscription-streams stream-id ind]
  (let [stream-thing (filter #(= stream-id (get % :id)) subscription-streams)]
    ((get (first stream-thing) :stream)
     ind)))

(defn pos-or-zero [num] (if (pos? num) num 0))

(defn solve-strindicator-at-index [strindicator subscription-streams current-ind]
  (if (contains? strindicator :id)
    (let [stream-id (get strindicator :id)
          target-ind (pos-or-zero (- current-ind (or (get strindicator :shift) 0)))]
      (get-subscription-stream-val subscription-streams stream-id target-ind))
    (let [stgr-fn (get strindicator :fn)
          stgr-inputs (get strindicator :inputs)]
      (if (number? stgr-fn) stgr-fn
          (apply
           stgr-fn
           (mapv #(solve-strindicator-at-index % subscription-streams current-ind) stgr-inputs))))))

(defn solve-strindicator [strindicator num-data-points]
  (mapv
   (partial
    solve-strindicator-at-index
    strindicator
    subscription-streams)
   (range num-data-points)))

(def solution
  (solve-strindicator
   strindicator
   num-data-points))

(println solution)

