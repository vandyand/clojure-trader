(ns helpers)

(defn return-type->vec [return-type]
  (cond
    (= return-type "short-only") [0 -1]
    (= return-type "long-only") [0 1]
    (= return-type "ternary") [-1 0 1 0 0 0 0 0 0 0]))

(defn time-it [msg f & args]
  (println msg)
  (time (apply f args)))