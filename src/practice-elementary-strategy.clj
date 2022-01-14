(ns practice-elementary-strategy
  (:require [oz.core :as oz]))

(oz/start-server! 10667)

(do 
(defn strategy
  [input-data]
  (if (> (first input-data) (nth input-data 1)) 1 0))

(def input-stream-1 
  (with-meta
    (vec
     (map #(Math/sin %) (range 10)))
    {:name "input stream 1"}))

(def input-stream-2 
  (with-meta
    (vec
     (map #(Math/cos %) (range 10)))
    {:name "input stream 2"}))

(def sieve-stream
  (with-meta
    (vec
     (map
      #(strategy (vector (input-stream-1 %) (input-stream-2 %)))
      (range 10)))
    {:name "sieve stream"}))

(def target-stream
  (with-meta input-stream-1 {:name "target stream"}))

(def target-stream-delta
  (with-meta
    (into [0.0]
          (for [i (range (- (count target-stream) 1))]
            (- (target-stream (+ i 1)) (target-stream i))))
    {:name "target stream deltas"}))

(def return-stream
  (with-meta
    (loop [i 1 v (transient [0.0])]
      (if (< i 10)
        (recur (inc i) (conj! v (+ (v (- i 1)) (* (sieve-stream (- i 1)) (target-stream-delta i)))))
        (persistent! v))) {:name "return stream"}))



(defn format-stream-for-view [stream]
  (let [item  ((meta stream) :name)]
    (loop [i 0 v (transient [])]
      (if (< i 10)
        (recur (inc i) (conj! v {:item item :x i :y (stream i)}))
        (persistent! v)))))

(def view-data
  (into [] (concat
            (format-stream-for-view input-stream-1)
            (format-stream-for-view input-stream-2)
            (format-stream-for-view sieve-stream)
            (format-stream-for-view return-stream))))

(def line-plot
  {:data {:values view-data}
   :encoding {:x {:field "x" :type "quantitative"}
              :y {:field "y" :type "quantitative"}
              :color {:field "item" :type "nominal"}}
   :mark {:type "line"}})

(def viz
  [:div [:vega-lite line-plot {:width 500}]])

(oz/view! viz))