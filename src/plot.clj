(ns plot
  (:require [file :as file]
            [oz.core :as oz]
            [v0_1_X.strategy :as strat]))

#_(oz/start-server! 10670)

(defn format-stream-for-view
  "returns a collection of view data (maps of form {:item <stream name> :x <x value> :y <y value>} )
   from the stream"
  [stream]
  (let [stream-name  (or (get (meta stream) :name) (strat/rand-suffix "noname"))]
    (loop [i 0 v (transient [])]
      (if (< i (count stream))
        (recur (inc i) (conj! v {:item stream-name :x i :y (stream i)})) ;; view data structure
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
  (let [first-val (first stream)]
    (mapv (fn [item] (- item first-val)) stream)))

(defn zero-instrument [instrument]
  (vec (for [price (map :o instrument)] (- price (:o (first instrument))))))

(defn plot-gaustrindies [gaustrindies]
  (let [streams (map #(-> % :fore-return-stream :beck) gaustrindies)
        values (format-streams-for-view streams)]
    (generate-and-view-plot values)))

(defn plot-stream [stream]
  (-> stream format-stream-for-view generate-and-view-plot))

(defn plot-streams [streams]
  (-> streams format-streams-for-view generate-and-view-plot))

(defn plot-with-intentions
  ([plotee intention-streams] (plot-with-intentions plotee intention-streams :return-stream))
  ([plotee intention-streams return-key]
   (let [return-streams (map #(-> % return-key :beck) plotee)
         zeroed-intention-streams (map zero-instrument intention-streams)
         all-streams (into return-streams zeroed-intention-streams)
         values (format-streams-for-view all-streams)]
     (generate-and-view-plot values))))

(defn format-performance-data
  "performance data is a collection of maps of keys (:time :mean :001 :002 ... :n)"
  [perf]
  (flatten
   (for [_key (filter #(not= % :time) (-> perf first keys))]
     (loop [i 0 v (transient [])]
       (if (< i (count perf))
         (recur (inc i) (let [perf-inst (nth perf i)]
                          (conj! v {:item (str _key) :x (:time perf-inst) :y (_key perf-inst)}))) ;; view data structure
         (persistent! v))))))

(comment
  (do
    (def perf-data (file/read-data-file "performance.edn" #"\r\n"))
       (generate-and-view-plot (format-performance-data perf-data)))                                                                                                                                                                                                                                                        

  ;; end comment
  )
