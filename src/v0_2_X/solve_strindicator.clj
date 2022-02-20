(ns v0_2_X.solve_strindicator
  (:require [stats :as stats]
            [clojure.pprint :as pp]))

(def num-data-points 10)

(def practice-strindicator {:inputs [{:id 0}
                                     {:inputs [{:id 0 :shift 0}]
                                      :fn #(+ 1 %)}
                                     {:inputs [{:id 0}
                                               {:inputs [{:id 0 :shift 0}]
                                                :fn #(+ % 1)}]
                                      :fn #(+ 1 %1 %2)}]
                            :fn (fn [& args] (reduce + args))})

(defn get-subscription-streams [num-data-points]
  [{:id 0 :stream (vec (range num-data-points))}
   {:id 1
    :stream [1.13104 1.12975 1.12947 1.12943 1.13064 1.13053 1.1306 1.13118 1.13106 1.13188 1.13174 1.13192 1.13174 1.13219 1.13126 1.13461 1.13462 1.13482 1.1346 1.13408 1.13558 1.13219 1.13548 1.13626 1.13588 1.13554 1.13596 1.13582 1.1358 1.13578 1.13553 1.13573 1.13521 1.13472 1.1346 1.1348 1.13539 1.13636 1.13754 1.13898 1.13774 1.13806 1.13852 1.13656 1.1363 1.13653 1.13654 1.13808 1.13744 1.1377 1.13905 1.1382 1.13736 1.1376 1.13728 1.13796 1.13818 1.13828 1.13363 1.13422 1.13566 1.13604 1.13752 1.13584 1.13614 1.13755 1.13656 1.13778 1.13594 1.13594 1.13694 1.13628 1.13593 1.13628 1.13642 1.13601 1.13625 1.13614 1.13637 1.13598 1.13682 1.1367 1.13675 1.13638 1.1366 1.13709 1.137 1.13758 1.1371 1.1361 1.13626 1.13602 1.13491 1.13482 1.13411 1.13259 1.13224 1.13302 1.13312 1.13249]}])

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
    (let [strind-fn (get strindicator :fn)
          strind-inputs (get strindicator :inputs)]
      (if (number? strind-fn) strind-fn
          (let [solution (apply strind-fn (mapv #(solve-strindicator-at-index % subscription-streams current-ind) strind-inputs))]
            (if (Double/isNaN solution) 0.0 solution))))))

(defn solve-strindicator [strindicator num-data-points]
  (mapv (partial solve-strindicator-at-index strindicator (get-subscription-streams num-data-points))
        (range num-data-points)))

(def solution (solve-strindicator practice-strindicator num-data-points))

(println solution)

