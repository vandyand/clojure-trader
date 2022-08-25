(ns nean.arena
  (:require [api.oanda_api :refer [get-account-balance]]
            [clojure.core.async :as async]
            [config :as config]
            [env :as env]
            [nean.ga :as ga]
            [nean.xindy2 :as x2]
            [stats :as stats]
            [uncomplicate.neanderthal.core :refer :all]
            [uncomplicate.neanderthal.native :refer :all]
            [util :as util]
            [v0_2_X.plot :as plot]
            [v0_2_X.streams :as streams]
            [v0_3_X.arena :as arena]))

(defn get-robustness [back-xindy fore-xindy]
  (stats/z-score (-> back-xindy :rivulet seq) (-> fore-xindy :rivulet seq)))

(defn combine-xindy [back-xindy fore-xindy]
  {:back back-xindy :fore fore-xindy :robustness (get-robustness back-xindy fore-xindy)})

(defn combine-xindies [back-xindies fore-xindies]
  (map combine-xindy back-xindies fore-xindies))

(defn get-robust-xindies [num-generations pop-config xindy-config back-stream fore-stream]
  (let [best-xindies (ga/get-parents (ga/run-generations num-generations pop-config xindy-config back-stream) pop-config)
        fore-xindies (for [xindy best-xindies]
                       (x2/get-xindy-from-shifts (:shifts xindy) (:max-shift xindy-config) fore-stream))
        full-xindies (combine-xindies best-xindies fore-xindies)]
    (filterv #(> (:robustness %) -0.25) full-xindies)))

(defn get-wrapped-rindies [instrument xindy-config pop-config granularity num-generations big-stream-count back-len-pct]
  (let [big-stream (dv (streams/get-big-stream instrument granularity big-stream-count))
        back-len (int (* (dim big-stream) back-len-pct))
        back-stream (subvector big-stream 0 back-len)
        fore-stream (subvector
                     big-stream
                     (- back-len (:max-shift xindy-config))
                     (- (dim big-stream) back-len (:max-shift xindy-config)))]
    {:instrument instrument
     :rindies (get-robust-xindies num-generations pop-config xindy-config back-stream fore-stream)}))

(defn get-wrapped-rindieses [instruments xindy-config pop-config granularity num-generations big-stream-count back-len-pct]
  (vec
   (for [instrument instruments]
     (get-wrapped-rindies instrument xindy-config pop-config granularity num-generations big-stream-count back-len-pct))))

(defn num-weekend-bars [granularity]
  (let [secs-per-bar (util/granularity->seconds granularity)
        secs-per-weekend (* 60 60 24 2)]
    (int (/ secs-per-weekend secs-per-bar))))

(defn get-new-xindies-from-wrapped-rindies [wrapped-rindies xindy-config granularity]
  (let [new-stream (dv (streams/get-big-stream (:instrument wrapped-rindies) granularity (+ (num-weekend-bars granularity) (* 2 (:max-shift xindy-config)))))]
    (for [rindy (:rindies wrapped-rindies)]
      (x2/get-xindy-from-shifts (-> rindy :back :shifts) (:max-shift xindy-config) new-stream))))

(defn get-position-from-xindies [xindies]
  (int (* (get-account-balance) (stats/mean (map #(-> % :sieve seq last) xindies)))))

(defn run-wrapped-rindieses [wrapped-rindieses xindy-config granularity]
  (let [schedule-chan (async/chan)]
    (util/put-future-times schedule-chan (util/get-future-unix-times-sec granularity))
    (async/go-loop []
      (when-some [val (async/<! schedule-chan)]
        (doseq [wrapped-rindies wrapped-rindieses]
          (async/go
            (arena/post-target-pos
             (:instrument wrapped-rindies)
             (get-position-from-xindies
              (get-new-xindies-from-wrapped-rindies
               wrapped-rindies
               xindy-config
               granularity))))))
      (when (not (env/get-env-data :KILL_GO_BLOCKS?)) (recur)))))

(comment
  (def xindy-config (config/get-xindy-config 8 1000))
  (def pop-config (ga/xindy-pop-config 200 80 0.4 0.45))
  (def granularity "H2")

  (def wrapped-rindieses (get-wrapped-rindieses
                          ["EUR_USD" "USD_JPY" "EUR_GBP" "AUD_USD" "EUR_JPY" "GBP_USD"
                           "USD_CHF" "AUD_JPY" "USD_CAD" "CHF_JPY" "EUR_CHF" "CAD_CHF"
                           "NZD_USD" "EUR_CAD" "NZD_JPY" "AUD_CHF" "CAD_JPY"]
                          xindy-config pop-config granularity 20 100000 0.95))

  (map #(-> wrapped-rindieses (nth %) :rindies count) (range (count wrapped-rindieses)))

  (run-wrapped-rindieses wrapped-rindieses xindy-config granularity)
)

(comment

  (def xindy-config (config/get-xindy-config 8 1000))
  (def pop-config (ga/xindy-pop-config 200 80 0.4 0.4))
  (def granularity "S15")

  (def wrapped-rindieses (get-wrapped-rindieses
                          ["EUR_USD" "AUD_USD" "USD_JPY"]
                          xindy-config pop-config granularity 5 100000 0.95))

  (map #(-> wrapped-rindieses (nth %) :rindies count) (range (count wrapped-rindieses)))

  (doseq [wrapped-rindies wrapped-rindieses]
    (let [new-xindies (get-new-xindies-from-wrapped-rindies wrapped-rindies xindy-config granularity)
          target-pos (get-position-from-xindies new-xindies)]
      (arena/post-target-pos
       (:instrument wrapped-rindies)
       target-pos)))

  (let [schedule-chan (async/chan)
        future-times (util/get-future-unix-times-sec granularity)]

    (util/put-future-times schedule-chan future-times)

    (async/go-loop []
      (when-some [val (async/<! schedule-chan)]
        (doseq [wrapped-rindies wrapped-rindieses]
          (async/go
            (arena/post-target-pos
             (:instrument wrapped-rindies)
             (get-position-from-xindies
              (get-new-xindies-from-wrapped-rindies
               wrapped-rindies
               xindy-config
               granularity))))))
      (when (not (env/get-env-data :KILL_GO_BLOCKS?)) (recur)))))

(comment

  (def max-shift 1000)
  (def back-len-pct 90)

  (def xindy-config (config/get-xindy-config 8 1000))
  (def pop-config (ga/xindy-pop-config 200 80 0.4 0.4))

  (def natural-big-stream (streams/get-big-stream "EUR_USD" "H1" 100000))

  (def big-stream (dv natural-big-stream))

  (def back-len (int (* (dim big-stream) back-len-pct 0.01)))

  (def back-stream (subvector big-stream 0 back-len))

  (def fore-stream (subvector
                    big-stream
                    (- back-len (:max-shift xindy-config))
                    (- (dim big-stream) back-len (:max-shift xindy-config))))

  (def rindies (get-robust-xindies 100 pop-config xindy-config back-stream fore-stream))

  (def mostr (first (reverse (sort-by :robustness rindies))))

  (def mostrs (filterv #(> (-> % :robustness) -0.25) rindies))

  (plot/plot-streams [(vec (reductions + (-> mostr :back :rivulet seq)))
                      (plot/zero-stream (seq (subvector
                                              back-stream
                                              (:max-shift xindy-config)
                                              (- (dim back-stream) (:max-shift xindy-config)))))])
  (plot/plot-streams [(vec (reductions + (-> mostr :fore :rivulet seq)))
                      (plot/zero-stream (seq (subvector
                                              fore-stream
                                              (:max-shift xindy-config)
                                              (- (dim fore-stream) (:max-shift xindy-config)))))])
  (plot/plot-streams [(vec (into (vec (reductions + (-> mostr :back :rivulet seq))) (vec (reductions + (-> mostr :fore :rivulet seq))))) (plot/zero-stream (seq big-stream))])

;;   (def best-pop (ga/run-generations 100 pop-config xindy-config back-stream))

;;   (def best-xindy (first best-pop))

;;   (def best-xindy-fore (x2/get-xindy-from-shifts (:shifts best-xindy) (:max-shift xindy-config) fore-stream))

  ;; end comment
  )





