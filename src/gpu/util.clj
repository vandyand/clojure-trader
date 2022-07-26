(ns gpu.util
  (:require
   [uncomplicate.clojurecuda.core :as cuda]
   [uncomplicate.commons.core :as commons]
   [uncomplicate.clojurecuda.info :as info]
   [util :as util]))

(defn gpu-init []
  (cuda/init)
  (-> 0 cuda/device cuda/context cuda/current-context!))

(defmacro type->bytesize [arg]
 `(-> ~arg type str (clojure.string/split #" ") last (str "/BYTES") symbol eval))

(defmacro memcpy-host!-batch [& args]
  `(do ~@(for [arg (partition 2 args)] `(apply println ~(vec arg)))))

(defmacro gpu-fn [kernel-fn kernel-fn-name & kernel-args]
  (let [num-elements (count (first kernel-args))
        bytesize (type->bytesize (ffirst kernel-args))
        num-bytes (* num-elements bytesize)
        gxs (cuda/mem-alloc num-bytes)
        gys (cuda/mem-alloc num-bytes)]
    (cuda/memcpy-host! (first kernel-args) gxs)
    (cuda/memcpy-host! (second kernel-args) gys)
    (let [gpu-fn (-> kernel-fn cuda/program cuda/compile! cuda/module (cuda/function kernel-fn-name))]
      (cuda/launch! gpu-fn (cuda/grid-1d num-elements) (cuda/parameters (-> num-elements (/ 10) int) gxs gys))
      (cuda/memcpy-host! gxs (double-array num-elements)))))

(defmacro asd [_one _two & _more]
  (list 'let [(vec ())]))


(defn print&eval [_form]
  (println _form)
  (eval _form))




(print&eval (list 'let '[[x y] [0 1]] '(println x y)))



(flatten (for [abc (-> 3 range vec)] (list (util/rand-caps-str) abc)))


(let [{a 0 b 1} [2 3]]
  (println a b)
  )

(let [[a b][7 6]] [b a])


(defmacro with-args
  {:style/indent 1}
  [argv arg-bindings & body]
  (let [bind-list (->> (partition 2 arg-bindings)
                       (map-indexed (fn [i v]
                                      [(first v) i]))
                       flatten)
        bind-form (-> (apply hash-map bind-list)
                      (assoc :or (apply hash-map arg-bindings)))
        bind-arg (vec argv)]
    `(let [~bind-form ~bind-arg]
       ~@body)))

(eval (macroexpand '(with-args [1674] [a 98 b 34 c 56 d 76] (println a b c d))))






