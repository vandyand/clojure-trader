(ns practice-tree-strategy
  (:require
   [clojure.spec.alpha :as s]
   [clojure.spec.gen.alpha :as gen]))

(comment 
  "This file contains a manually-created practice tree with a solver")

(s/def :sine/amp (s/double-in :min (-> p :amp :min) :max (-> p :amp :max) :NaN? false :infinite? false))
(s/def :sine/freq (s/double-in :min (-> p :freq :min) :max (-> p :freq :max) :NaN? false :infinite? false))
(s/def :sine/angle (s/int-in 0 1000000))
(s/def :sine/args (s/cat :sine/angle {:a :sine/amp :b :sine/freq :c :sine/h-shift :d :sine/v-shift}))

(s/fdef sine
  :args :sine/args
  :ret number?)

;; (s/fdef :strategy/condition)
;; (s/def :strategy/branch (s/or :strategy/node boolean))
;; (s/def :strategy/node)


(def node4 {:id 4 :input-indxs [1 0] :branchA false :branchB true})
(def node3 {:id 3 :input-indxs [1 3] :branchA true :branchB false})
(def node2 {:id 2 :input-indxs [1 2] :branchA node3 :branchB node4})
(def node1 {:id 1 :input-indxs [2 0] :branchA node2 :branchB true})
(def inputs [10 2 6 4])

(defn recur-nodes [node]
  (if (= (type node) java.lang.Boolean)
    node
    (recur-nodes
     (if (>
          (nth inputs (first (node :input-indxs)))
          (nth inputs (last (node :input-indxs))))
       (node :branchA)
       (node :branchB)))))

(recur-nodes node1)

(s/def ::bool boolean?)
(s/def ::node (s/or ::bool (s/and ::input-indxs ::branchA ::branchB)))
(s/def ::input-indx (s/int-in 0 10))
(s/def ::input-indxs (s/coll-of ::input-indx :count 2 :distinct true))
(s/def ::branchA ::node)
(s/def ::branchB ::node)
(binding [s/*recursion-limit* 1] (gen/generate (s/gen ::node)))

(def tree {:cond #(> (nth inputs 1) (nth inputs 2)) 
           :branchA {:cond #(> (nth inputs 0) (nth inputs 1))
                     :branchA {:cond #(> (nth inputs 0) (nth inputs 3)) :branchA true :branchB false} 
                     :branchB {:cond #(> (nth inputs 3) (nth inputs 1)) :branchA false :branchB true}} 
           :branchB {:cond #(> (nth inputs 3) (nth inputs 2)) 
                     :branchA false 
                     :branchB {:cond #(> (nth inputs 0) (nth inputs 2)) :branchA true :branchB false}}})

(defn recur-tree [tree]
  (if (= (type tree) java.lang.Boolean)
    tree
    (recur-tree
     (if ((tree :cond))
       (tree :branchA)
       (tree :branchB)))))

(recur-tree tree)
