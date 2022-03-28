(ns v0_2_X.plot
  (:require [oz.core :as oz]
            [v0_1_X.incubator.strategy :as strat]))

(oz/start-server! 10668)

(defn format-stream-for-view
  "returns a collection of view data (maps of form {:item <stream name> :x <x input angle> :y <stream solution at x>} )
   from the stream"
  [stream]
  (let [item  (or (get (meta stream) :name) (strat/rand-suffix "noname"))]
    (loop [i 0 v (transient [])]
      (if (< i (count stream))
        (recur (inc i) (conj! v {:item item :x i :y (stream i)})) ;; view data structure
        (persistent! v)))))

(defn format-streams-for-view [streams]
  (flatten (for [stream streams] (format-stream-for-view stream))))

(defn generate-and-view-plot [values]
  (let [viz
        [:div
         [:vega-lite
          {:data
           {:values values}
           :encoding {:x {:field "x" :type "quantitative"}
                      :y {:field "y" :type "quantitative"}
                      :color {:field "item" :type "nominal"}}
           :mark {:type "line"}} {:width 500}]]]
    (oz/view! viz)))

(defn zero-stream [stream]
  (vec (for [price stream] (- price (first stream)))))

(defn plot-ghystrindies [ghystrindies]
  (let [streams (map #(-> % :g-return-streams first :sum-beck) ghystrindies)
        values (format-streams-for-view streams)]
  (generate-and-view-plot values)))

(defn plot-with-intentions 
  ([plotee intention-streams] (plot-with-intentions plotee intention-streams :return-streams))
  ([plotee intention-streams return-key]
  (let [return-streams (map #(-> % return-key first :sum-beck) plotee)
        zeroed-intention-streams (map zero-stream intention-streams)
        all-streams (into return-streams zeroed-intention-streams)
        values (format-streams-for-view all-streams)]
    (generate-and-view-plot values))))