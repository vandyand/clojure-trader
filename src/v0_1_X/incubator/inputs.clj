(ns v0_1_X.incubator.inputs
  (:require [v0_1_X.incubator.sine_waves :as sw]))

(defn scaled-rand
  "returns random double between min (inclusive) and max (exclusive)"
  [min max]
  (-> (- max min) (rand) (+ min)))

(defn get-rand-sine-config [rand-sine-template-config]
  (let [rand-amp (scaled-rand 0 (get rand-sine-template-config :max-amp))
        rand-freq (scaled-rand 0 (get rand-sine-template-config :max-freq))
        rand-h-shift (scaled-rand 0 (get rand-sine-template-config :max-h-shift))
        rand-v-shift (scaled-rand 0 (get rand-sine-template-config :max-v-shift))
        args {:amp rand-amp :freq rand-freq :h-shift rand-h-shift :v-shift rand-v-shift}
        name (sw/get-sine-fn-name args)]
    {:name name
     :args args
     :fn (fn [x]
           (-> x
               (* rand-freq)
               (- rand-h-shift)
               (Math/sin)
               (* rand-amp)
               (+ rand-v-shift)))}))

(defn get-sine-configs [base-config num-key]
  (vec (repeatedly (get base-config num-key) #(get-rand-sine-config base-config))))

(defn get-rand-sine-template-config [max-amp max-freq max-v-shift max-h-shift]
  {:max-amp max-amp
   :max-freq max-freq
   :max-v-shift max-v-shift
   :max-h-shift max-h-shift})

(defn get-sine-inputs-config [num-inception-streams num-intention-streams num-data-points max-amp max-freq max-v-shift max-h-shift]
  (let [base-config {:num-inception-streams num-inception-streams
                     :num-intention-streams num-intention-streams
                     :num-data-points num-data-points
                     :max-amp max-amp
                     :max-freq max-freq
                     :max-v-shift max-v-shift
                     :max-h-shift max-h-shift}]
    (assoc base-config
           :inception-streams-config (get-sine-configs base-config :num-inception-streams)
           :intention-streams-config (get-sine-configs base-config :num-intention-streams))))
