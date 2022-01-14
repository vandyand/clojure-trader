(ns strategy
  (:require
   [clojure.spec.alpha :as s]
   [clojure.spec.gen.alpha :as sgen]
   [clojure.test.check.generators :as gen]
   [clojure.string :as cs]))


(s/def ::cond ifn?)
(s/def ::branch ::node)

(s/def ::node
  (s/or :bool boolean?
        :node (s/keys :req [::cond ::branch])))


(s/def ::with-h
  (s/with-gen
    #(cs/includes? % "h")
    #(gen/fmap
      (fn [[s1 s2]] (str s1 "h" s2))
      (gen/tuple (gen/string-alphanumeric) (gen/string-alphanumeric)))))
(gen/sample (s/gen ::with-h) 5)



(s/def ::branchA #{:branchA})
(s/def ::branchB #{:branchB})
(s/def ::map-tree (s/map-of ::branchA (s/or :tree ::map-tree :leaf boolean?) :gen-max 3))


(s/def ::boo number?)
(s/def ::baz string?)
(s/def ::bez boolean?)
(s/def ::xed (s/keys :req [(or ::boo ::bez)]))
(s/def ::wut (s/keys :req [(or ::boo ::baz)]))
(s/def ::wiz (s/map-of keyword? int?))
(gen/sample (s/gen ::wiz) 5)
(s/def ::xor (s/or :k1 ::wut :k2 boolean?))
(gen/sample (s/gen ::xor) 5)

; node is either a map of 
; {:condition (which is a function taking two number inputs and outputting a boolean)
;  :branches (which is a vector of two branches which are other nodes)} implying a branch is either a map or a bool
; OR 
; a boolean value

(defn condition [i1 i2] (> i1 i2))
(s/fdef condition
  :args (s/cat :i1 number? :i2 number?)
  :ret boolean?)

(s/exercise-fn `condition)


(s/def ::hello
  (s/with-gen #(cs/includes? % "hello")
    #(sgen/fmap (fn [[s1 s2]] (str s1 "hello" s2))
                (sgen/tuple (sgen/string-alphanumeric) (sgen/string-alphanumeric)))))

(s/def ::map-nodes (s/map-of ::hello (s/or :node ::map-nodes :exit boolean?) :gen-max 3))



(comment
 ; just make the function that returns the tree?
;; (def tree {:cond #(> (nth inputs 1) (nth inputs 2)) 
;;            :branchA {:cond #(> (nth inputs 0) (nth inputs 1))
;;                      :branchA {:cond #(> (nth inputs 0) (nth inputs 3)) :branchA true :branchB false} 
;;                      :branchB {:cond #(> (nth inputs 3) (nth inputs 1)) :branchA false :branchB true}} 
;;            :branchB {:cond #(> (nth inputs 3) (nth inputs 2)) 
;;                      :branchA false 
;;                      :branchB {:cond #(> (nth inputs 0) (nth inputs 2)) :branchA true :branchB false}}})

; Another example tree
;;   (def tree {:input-indxs [4 0], 
;;  :branchA {:input-indxs [3 4], 
;;            :branchA {:input-indxs [2 3], 
;;                      :branchA {:input-indxs [2 0], 
;;                                :branchA true, 
;;                                :branchB {:input-indxs [3 1], 
;;                                          :branchA true, 
;;                                          :branchB {:input-indxs [3 3], 
;;                                                    :branchA true, 
;;                                                    :branchB false}}}, 
;;                      :branchB false}, 
;;            :branchB {:input-indxs [2 3], 
;;                      :branchA {:input-indxs [4 3], 
;;                                :branchA false, 
;;                                :branchB true}, 
;;                      :branchB false}}, 
;;  :branchB {:input-indxs [3 3], 
;;            :branchA {:input-indxs [1 0], 
;;                      :branchA false, 
;;                      :branchB false}, 
;;            :branchB {:input-indxs [1 3], 
;;                      :branchA {:input-indxs [3 2], 
;;                                :branchA false, 
;;                                :branchB false}, 
;;                      :branchB {:input-indxs [1 0], 
;;                                :branchA true, 
;;                                :branchB false}}}})
  )

(def index-pairs
  (filter
   #(not= (first %) (last %))
   (for [x (range 5) y (range 5)] [x y])))

(defn make-tree
  ([] (make-tree {}))
  ([tree]
   (if (> (rand) 0.35)
     (rand-nth [true false])
     {:input-indxs (rand-nth index-pairs)
      :branchA (make-tree tree)
      :branchB (make-tree tree)})))

(def inputs [10 20 30 40 50])

(defn solve-cond [input-indxs]
  (> (inputs (first input-indxs)) (inputs (last input-indxs))))

(defn solve-tree [tree]
  (if (= (type tree) java.lang.Boolean)
    tree
    (solve-tree
     (if (solve-cond (tree :input-indxs))
       (tree :branchA)
       (tree :branchB)))))

(defn print-tree [tree]
  (println tree)
  tree)

(time (solve-tree (print-tree (make-tree))))
