(ns index
  (:require
   [oz.core :as oz]
   [clojure.spec.alpha :as s]
   [clojure.spec.gen.alpha :as gen]))

(oz/start-server! 10667)

(s/def :sine/amp (s/double-in :min 1 :max 10 :NaN? false :infinite? false))
(s/def :sine/freq (s/double-in :min 0 :max 0.01 :NaN? false :infinite? false))
(s/def :sine/h-shift (s/double-in :min -1000 :max 1000 :NaN? false :infinite? false))
(s/def :sine/v-shift (s/double-in :min -100 :max 100 :NaN? false :infinite? false))
(s/def :sine/angle (s/int-in 0 1000000))
(s/def :sine/args (s/cat :a :sine/amp :b :sine/freq :c :sine/h-shift :d :sine/v-shift))


(defn sine
  ([x a b c] (sine x a b c 0))
  ([x a b c d]
   "Sine wave of form: y = a*sin(bx-c)+d. 
     Amplitude is abs(a), frequency is abs(b)/(2*PI), 
     horizontal shift is c, and vertical shift is d"
   (-> x (* b) (- c) (Math/sin) (* a) (+ d))))

(s/fdef sine
  :args :sine/args
  :ret number?)

(s/exercise-fn `sine)

(do
  
  (def generated-sine-data (gen/generate (s/gen :sine/args)))
  
  (defn sine-fn-str [args] (apply #(format "y=%.3f*sin(%.4fx-%.2f)+%.2f" %1 %2 %3 %4) args))
  
  (defn make-sine-fn [args]
    (fn [i] (apply (partial sine i) args)))

  (defn data [& names]
    (for [n names
          x (range 2000)]
      
      (let [sine-fn (make-sine-fn generated-sine-data)]
        {:item n :x x :y (sine-fn x)})))

  (def values (data (sine-fn-str generated-sine-data)))
  
  (def line-plot
    {:data {:values values}
     :encoding {:x {:field "x" :type "quantitative"}
                :y {:field "y" :type "quantitative"}
                :color {:field "item" :type "nominal"}}
     :mark {:type "line"}
     })

  (def viz
    [:div [:vega-lite line-plot {:width 200}]])

  (oz/view! viz))


(s/def :ex/dubs (s/double-in))
(gen/sample (s/gen :ex/dubs) 100)
