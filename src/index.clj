(ns index
  (:require
   [oz.core :as oz]))

(oz/start-server! 10667)

(do
  (defn data [& names]
    (for [n names
          i (range 2000)]
      {:time i :item n :quantity (+ (Math/sin (/ i 180)) (-> (rand) (* 2) (- 1)))}))

  (def line-plot
    {:data {:values (data "sine")}
     :encoding {:x {:field "time" :type "quantitative"}
                :y {:field "quantity" :type "quantitative"}
                :color {:field "item" :type "nominal"}}
     :mark "line"})

  (def viz
    [:div [:vega-lite line-plot {:width 1000}]])

  (oz/view! viz))