(ns v0_1_X.sine_waves
  (:require
   [oz.core :as oz]
   [clojure.spec.alpha :as s]
  ;;  [clojure.spec.gen.alpha :as gen]
   ))

(comment
  "This file creates a bunch of sine waves and plots them. 
   It also plots the running sum of all the sine waves (the reduced wave? well it uses a reducer...)")

;; (oz/start-server! 10668)

(def num-waves 20)
(def num-data-points 100)
(def freq-scale-factor 2)
(defn min-max [min max]
  {:min min :max max})
(def params-range {:amp (min-max 1 10) :h-shift (min-max -10000 10000) :v-shift (min-max 0 10)})
(defn scale-inv [val factor]
  (-> val (* factor) (Math/pow -1)))
(defn scaled-rand [min max]
  (-> (- max min) (rand) (+ min)))
(def p (assoc params-range :freq
              {:min (scale-inv (get-in params-range [:amp :max]) freq-scale-factor)
               :max (scale-inv (get-in params-range [:amp :min]) freq-scale-factor)}))

(s/def :sine/amp (s/double-in :min (-> p :amp :min) :max (-> p :amp :max) :NaN? false :infinite? false))
(s/def :sine/freq (s/double-in :min (-> p :freq :min) :max (-> p :freq :max) :NaN? false :infinite? false))
(s/def :sine/h-shift (s/double-in :min (-> p :h-shift :min) :max (-> p :h-shift :max) :NaN? false :infinite? false))
(s/def :sine/v-shift (s/double-in :min (-> p :v-shift :min) :max (-> p :v-shift :max) :NaN? false :infinite? false))
(s/def :sine/angle (s/int-in 0 1000000))
(s/def :sine/args (s/cat :sine/angle {:a :sine/amp :b :sine/freq :c :sine/h-shift :d :sine/v-shift}))

(defn sine
  "solves a sine wave of form: y = amp * sin(freq * x - h-shift) + v-shift.
     where Amplitude is abs(amp), frequency is abs(freq)/(2*PI), 
     horizontal shift is h-shift, and vertical shift is v-shift
   Inputs: 
   x: number - angle at which to solve sine funtion for
   fn-constants: map of form {:amp :freq :h-shift :v-shift} containing 
                 sine function constants 
    "
  ([x fn-constants]
   (-> x
       (* (fn-constants :freq))
       (- (fn-constants :h-shift))
       (Math/sin)
       (* (fn-constants :amp))
       (+ (fn-constants :v-shift)))))

(s/fdef sine
  :args :sine/args
  :ret number?)

(defn get-sine-fn-name [args]
  (format "y=%.3f*sin(%.4fx-%.0f)+%.2f" (args :amp) (args :freq) (args :h-shift) (args :v-shift)))

(defn get-sine-fn
  "takes in a map with keys {:amp :freq :h-shift :v-shift}
     returns composed sine function which only takes (and then solves) one input (angle)"
  [args]
  (fn [i] (apply (partial sine i) [args])))

(defn get-rand-sine-fn-params
  "returns num number of maps of form {:amp <amplitude> :freq <frequency> :h-shift <horizontal shift> :v-shift <vertical shift>}
     (keys not necessarily in that order)"
  [num]
  (repeatedly num (fn [] (into {} (for [k (keys p)] {k (scaled-rand (get-in p [k :min]) (get-in p [k :max]))})))))

(defn get-rand-sine-fns
  "returns num number of maps of form {:name <sine func name> :fn <actual function>}"
  ([] (get-rand-sine-fns 1))
  ([num]
   (for [data (get-rand-sine-fn-params num)] {:name (get-sine-fn-name data) :fn (get-sine-fn data)})))

(defn generate-plot-values []
  (for [d (get-rand-sine-fns num-waves)
        x (range num-data-points)]
    {:item (d :name) :x x :y ((d :fn) x)}))

(comment
  (def values (generate-plot-values))

  (def reduced-vals (for [x (range num-data-points)]
                      {:item "reduced"
                       :x x
                       :y (reduce #(+ (get %2 :y) %1) 0
                                  (filter #(= (get % :x) x) values))}))

  (def line-plot
    {:data {:values (into reduced-vals values)}
     :encoding {:x {:field "x" :type "quantitative"}
                :y {:field "y" :type "quantitative"}
                :color {:field "item" :type "nominal"}}
     :mark {:type "line"}})

  (def viz
    [:div [:vega-lite line-plot {:width 500}]])

  (oz/view! viz)
  )
