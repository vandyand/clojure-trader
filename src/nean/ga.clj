(ns nean.ga
  (:require [api.oanda_api :as oa]
            [api.order_types :as ot]
            [clojure.core.async :as async]
            [config :as config]
            [env :as env]
            [helpers :as hlp]
            [stats :as stats]
            [uncomplicate.fluokitten.core :refer [fmap]]
            [uncomplicate.neanderthal.core :refer :all]
            [uncomplicate.neanderthal.native :refer :all]
            [util :as util]
            [plot :as plot]
            [v0_2_X.streams :as streams]
            [v0_3_X.arena :as arena]
            [nean.xindy2 :as x2]))

(defn in-range [val range-low range-high]
  (and (>= val range-low) (<= val range-high)))

(defn mutate-shifts [shifts max-shift]
  (mapv
   (fn [shift]
     (let [new-shift (if (hlp/rand-bool) shift (-> 41 rand-int (- 20) (+ shift)))]
       (if (in-range new-shift 1 max-shift) new-shift shift)))
   shifts))

(defn mutate-xindy [xindy xindy-config stream]
  (let [new-shifts (mutate-shifts (:shifts xindy) (:max-shift xindy-config))]
    (x2/get-xindy-from-shifts new-shifts (:max-shift xindy-config) stream)))

(defn crossover-shifts [shifts]
  (mapv stats/mean-int (apply (partial map list) shifts)))

(defn crossover-xindies [xindies xindy-config stream]
  (let [new-shifts (crossover-shifts (map :shifts xindies))]
    (x2/get-xindy-from-shifts new-shifts (:max-shift xindy-config) stream)))

(defn sort-pop [pop]
  (->> pop (sort-by :score) reverse vec))

(defn get-init-pop [pop-config xindy-config stream]
  (sort-pop
   (for [i (range (:pop-size pop-config))]
     (x2/get-rand-xindy xindy-config stream))))

(defn xindy-pop-config [pop-size num-parents]
  (let [num-children (- pop-size num-parents)]
    {:pop-size pop-size :num-parents num-parents :num-children num-children}))

(defn xindy-ga-config [num-generations stream-count back-pct]
  {:num-generations num-generations :stream-count stream-count :back-pct back-pct})

(defn get-parents [pop pop-config]
  (take (:num-parents pop-config) pop))

(defn get-child [parents xindy-config stream]
  (if (= 1 (count parents))
    (mutate-xindy (first parents) xindy-config stream)
    (crossover-xindies parents xindy-config stream)))

(defn get-children [parents pop-config xindy-config stream]
  (vec
   (for [i (range (:num-children pop-config))]
     (let [child-num-parents (->> (range) (random-sample 0.5) first (+ 1))
          ;;  child-parents (repeatedly
          ;;                 child-num-parents
          ;;                 #(->> (range (:num-parents pop-config)) cycle
          ;;                       (random-sample 0.01) first (nth parents)))
           child-parents (repeatedly
                          child-num-parents
                          #(nth parents (util/rand-lin-dist 2 (:num-parents pop-config))))]
       (get-child child-parents xindy-config stream)))))

(defn run-generation [pop pop-config xindy-config stream]
  (let [_parents (get-parents pop pop-config)
        _children (get-children _parents pop-config xindy-config stream)]
    (sort-pop (into _parents _children))))

(defn run-generations
  ([num-generations pop-config xindy-config stream] (run-generations (get-init-pop pop-config xindy-config stream) num-generations pop-config xindy-config stream))
  ([starting-pop num-generations pop-config xindy-config stream]
   (loop [i 1 pop starting-pop]
     (when (env/get-env-data :GA_LOGGING?) (println i (-> pop first :score) (stats/mean (map :score pop))))
    ;;  (plot/plot-streams [(->> pop first :rivulet seq vec (reductions +) vec)
    ;;                      (->> pop second :rivulet seq vec (reductions +) vec)
    ;;                      (plot/zero-stream (-> stream seq vec (subvec (:max-shift xindy-config))))])
     (if (< i num-generations)
       (recur (inc i) (run-generation pop pop-config xindy-config stream))
       pop))))

(comment
  (clojure.pprint/pprint (sort (frequencies (take 10000 (repeatedly (fn [] (first (random-sample (/ 1.0 5000) (->> (range) (map #(mod % 5000)))))))))))

  (def xindy-config (config/get-xindy-config 8 100))
  (def pop-config (xindy-pop-config 200 80))

  (def natural-big-stream (streams/get-big-stream "EUR_USD" "H1" 100000))

  (def big-stream (dv natural-big-stream))

  (def best-pop (run-generations 100 pop-config xindy-config big-stream))

  (def best-xindy (first best-pop))

  (plot/plot-streams [(vec (reductions + (-> best-xindy :rivulet seq))) (plot/zero-stream natural-big-stream)])
  (plot/plot-streams [(plot/zero-stream natural-big-stream)])

  ;; end comment
  )