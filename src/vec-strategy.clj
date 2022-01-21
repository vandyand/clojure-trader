(ns vec-strategy
  (:require
   [clojure.set :as set]))

(def num-inputs 4)
(defn get-input-indxs [num-inputs]
  (set
   (filter
    #(not (nil? %))
    (for [x (range num-inputs) y (range num-inputs)]
      (if (not= x y)  #{x y})))))

;; (defn children [] 
;;   (rand-nth [[true false] [(node) (rand-nth [true false]) [(node) (node)]]]))

(defn node
  ([] (node 0 4 (get-input-indxs num-inputs) #{}))
  ([depth max-depth input-indxs used-indxs] 
   (let [indx-pair (rand-nth (seq (set/difference input-indxs used-indxs)))]
    (let [new-node (fn [indx-pair] (node (inc depth) max-depth input-indxs (set/union used-indxs #{indx-pair})))]
     (let [children (if (>= depth max-depth)
                      (rand-nth [[true false] [false true]])
                      (let [n (rand-int 4)]
                        (cond (= n 0) [true false]
                              (= n 1) [false true]
                              (= n 2) [(new-node indx-pair) (rand-nth [true false])]
                              (= n 3) (let [indx-pair2 (rand-nth (seq (set/difference input-indxs used-indxs #{indx-pair})))]
                                        (println "index pairs: " indx-pair indx-pair2)
                                        [(new-node indx-pair) (new-node indx-pair2)]))))]
       (println "used indexes: " used-indxs)
       (println "node: " [indx-pair children])
       (println "-------------")
       [indx-pair children])))))

(node)

(def used-indxs #{#{1 3} #{3 2}})
(def input-indxs (get-input-indxs 4))

(do
  (def input-indx1 (rand-nth (seq (set/difference input-indxs used-indxs))))
  (def input-indx2 (rand-nth (seq (set/difference input-indxs used-indxs #{input-indx1}))))
  (println input-indx1 input-indx2))

(set/union #{#{1 3} #{3 2}} #{input-indx2})