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
   (for [_ (range (:pop-size pop-config))]
     (x2/get-rand-xindy xindy-config stream))))

(defn get-parents [pop pop-config]
  (take (:num-parents pop-config) pop))

(defn get-child [parents xindy-config stream]
  (if (= 1 (count parents))
    (mutate-xindy (first parents) xindy-config stream)
    (crossover-xindies parents xindy-config stream)))

(defn get-children [parents pop-config xindy-config stream]
  (vec
   (for [_ (range (:num-children pop-config))]
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
  ([num-generations pop-config xindy-config stream]
   (run-generations (get-init-pop pop-config xindy-config stream) num-generations pop-config xindy-config stream))
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

  (def xindy-config (config/get-xindy-config 8 500))
  (def pop-config (config/xindy-pop-config 2000 1000))

  (def natural-big-stream (streams/get-big-stream "GBP_CHF" "H1" 20000))

  (def big-stream (dv natural-big-stream))

  (def best-pop (run-generations 0 pop-config xindy-config big-stream))

  (def decent-pop (->> best-pop (filter #(> (:score %) 0))))
  (def decent-pop2 (->> best-pop (filter #(> (:score %) 0))))
  (def decent-pop3 (->> best-pop (filter #(> (:score %) 0))))

  (def decent-pop4 (->> best-pop (filter #(> (:score %) 0))))
  (def decent-pop5 (->> best-pop (filter #(> (:score %) 0))))
  (def decent-pop6 (->> best-pop (filter #(> (:score %) 0))))
  (def decent-pop7 (->> best-pop (filter #(> (:score %) 0))))

  (def decent-pop8 (->> best-pop (filter #(> (:score %) 0))))
  (def decent-pop9 (->> best-pop (filter #(> (:score %) 0))))
  (def decent-pop10 (->> best-pop (filter #(> (:score %) 0))))
  (def decent-pop11 (->> best-pop (filter #(> (:score %) 0))))

  (def avg-riv (mapv stats/mean (apply (partial map list) (map #(-> % :rivulet seq) decent-pop))))
  (def avg-riv2 (mapv stats/mean (apply (partial map list) (map #(-> % :rivulet seq) decent-pop2))))
  (def avg-riv3 (mapv stats/mean (apply (partial map list) (map #(-> % :rivulet seq) decent-pop3))))
  
  (def avg-riv4 (mapv stats/mean (apply (partial map list) (map #(-> % :rivulet seq) decent-pop4))))
  (def avg-riv5 (mapv stats/mean (apply (partial map list) (map #(-> % :rivulet seq) decent-pop5))))
  (def avg-riv6 (mapv stats/mean (apply (partial map list) (map #(-> % :rivulet seq) decent-pop6))))
  (def avg-riv7 (mapv stats/mean (apply (partial map list) (map #(-> % :rivulet seq) decent-pop7))))

  (def avg-riv8 (mapv stats/mean (apply (partial map list) (map #(-> % :rivulet seq) decent-pop8))))
  (def avg-riv9 (mapv stats/mean (apply (partial map list) (map #(-> % :rivulet seq) decent-pop9))))
  (def avg-riv10 (mapv stats/mean (apply (partial map list) (map #(-> % :rivulet seq) decent-pop10))))
  (def avg-riv11 (mapv stats/mean (apply (partial map list) (map #(-> % :rivulet seq) decent-pop11))))

  (def avg-rivs (mapv stats/mean (apply (partial map list) [avg-riv
                                                            avg-riv2
                                                            avg-riv3
                                                            avg-riv4
                                                            avg-riv5
                                                            avg-riv6
                                                            avg-riv7
                                                            avg-riv8
                                                            avg-riv9
                                                            avg-riv10
                                                            avg-riv11])))

  (plot/plot-streams [(vec (reductions + avg-rivs))])
  (plot/plot-streams [(vec (reductions + avg-riv2)) (plot/zero-stream (subvec natural-big-stream 500))])
  (plot/plot-streams [(vec (reductions + (-> best-pop (nth 999) :rivulet seq))) (plot/zero-stream (subvec natural-big-stream 500))])
  (plot/plot-streams [(plot/zero-stream natural-big-stream)])

  ;; end comment
  )