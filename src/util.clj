(ns util)

(defn find-in [coll _key _val] 
  (reduce (fn [_ cur-val] (when (= (_key cur-val) _val) (reduced cur-val)))
        nil coll))