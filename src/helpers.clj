(ns helpers)

(defn return-type->vec [return-type]
  (cond
    (= return-type "short-only") [-1 0 0 0 0 0 0]
    (= return-type "long-only") [1 0 0 0 0 0 0]
    (= return-type "ternary") [-1 1 0 0 0 0 0 0 0]))

(defn time-it [msg f & args]
  ;; (apply f args)
  (let [t (time (apply f args))]
    (println msg)
    t)
  )