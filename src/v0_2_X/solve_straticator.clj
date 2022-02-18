(ns v0_2_X.solve_straticator
  (:require [stats :as stats]
            [clojure.pprint :as pp]
            [v0_2_X.build_straticator :as bstcr]))

(def num-data-points 10)

(def straticator {:straticator-fn
                  {:inputs [{:id 0}
                            {:straticator-fn
                             {:inputs [{:id 0 :shift 0}]
                              :fn #(+ 1 %)}}
                            {:straticator-fn
                             {:inputs [{:id 0}
                                       {:straticator-fn
                                        {:inputs [{:id 0 :shift 0}]
                                         :fn #(+ % 1)}}]
                              :fn #(+ 1 %1 %2)}}]
                   :fn (fn [& args] (reduce + args))}})

(def subscription-streams [{:id 0 :stream (vec (range num-data-points))}])

(defn get-subscription-stream-val [subscription-streams stream-id ind]
  (let [stream-thing (filter #(= stream-id (get % :id)) subscription-streams)]
    ((get (first stream-thing) :stream)
     ind)))

(defn pos-or-zero [num] (if (pos? num) num 0))

(defn solve-straticator-at-index [straticator subscription-streams current-ind]
  (if (contains? straticator :id)
    (let [stream-id (get straticator :id)
          target-ind (pos-or-zero (- current-ind (or (get straticator :shift) 0)))]
      (get-subscription-stream-val subscription-streams stream-id target-ind))
    (let [stcr-fn (get-in straticator [:straticator-fn :fn])
          stcr-inputs (get-in straticator [:straticator-fn :inputs])]
      (apply
       stcr-fn
       (mapv #(solve-straticator-at-index % subscription-streams current-ind) stcr-inputs)))))

(defn solve-straticator [straticator num-data-points]
  (mapv
   (partial
    solve-straticator-at-index
    straticator
    subscription-streams)
   (range num-data-points)))

(println (solve-straticator straticator num-data-points))
