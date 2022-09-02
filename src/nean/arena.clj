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
            [plot :as plot]
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

(defn get-wrapped-rindies [instrument xindy-config pop-config granularity ga-config]
  (let [foo (println instrument)
        big-stream (dv (streams/get-big-stream instrument granularity (:stream-count ga-config)))
        back-len (int (* (dim big-stream) (:back-pct ga-config)))
        fore-len (- (dim big-stream) back-len)
        back-stream (subvector big-stream 0 back-len)
        fore-stream (subvector
                     big-stream
                     (- back-len (:max-shift xindy-config))
                     (+ fore-len (:max-shift xindy-config)))]
    {:instrument instrument
     :rindies (get-robust-xindies (:num-generations ga-config) pop-config xindy-config back-stream fore-stream)}))

(defn get-wrapped-rindieses [instruments xindy-config pop-config granularity ga-config]
  (vec
   (for [instrument instruments]
     (get-wrapped-rindies instrument xindy-config pop-config granularity ga-config))))

(defn num-weekend-bars [granularity]
  (let [secs-per-bar (util/granularity->seconds granularity)
        secs-per-weekend (* 60 60 24 2)]
    (int (/ secs-per-weekend secs-per-bar))))

(defn get-new-xindies-from-wrapped-rindies [wrapped-rindies xindy-config granularity]
  (let [new-stream (dv (streams/get-big-stream
                        (:instrument wrapped-rindies)
                        granularity (+ 1000 (num-weekend-bars granularity) (* 2 (:max-shift xindy-config)))))]
    (for [rindy (:rindies wrapped-rindies)]
      (x2/get-xindy-from-shifts (-> rindy :back :shifts) (:max-shift xindy-config) new-stream))))

(defn get-position-from-xindies [xindies]
  (let [account-balance (get-account-balance)
        max-pos (int (* 10 account-balance))
        target-pos (int (* 0.25 account-balance (stats/mean (map #(-> % :sieve seq last) xindies))))]
    (cond
      (> target-pos max-pos) max-pos
      (< target-pos (* -1 max-pos)) (* -1 max-pos)
      :else target-pos)))

(defn run-wrapped-rindieses
  ([wr xc g] (run-wrapped-rindieses wr xc g (env/get-account-id)))
  ([wrapped-rindieses xindy-config granularity account-id]
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
                granularity))
              account-id))))
       (when (not (env/get-env-data :KILL_GO_BLOCKS?)) (recur))))))

(defn run-multi-wrapped-rindieses
  [instruments granularities account-ids xindy-config pop-config ga-config]
  (for [gran-account-id (partition 2 (interleave granularities account-ids))]
    (let [granularity (first gran-account-id)
          account-id (second gran-account-id)
          wrapped-rindieses (get-wrapped-rindieses instruments xindy-config pop-config granularity ga-config)
          filtered-rindieses (filter #(> (-> % :rindies count) 1) wrapped-rindieses)]
      (run-wrapped-rindieses filtered-rindieses xindy-config granularity account-id))))

(comment
  (def xindy-config (config/get-xindy-config 6 500))
  (def pop-config (ga/xindy-pop-config 400 160 0.4 0.6))
  (def ga-config (ga/xindy-ga-config 15 10000 0.8))
  (def instruments ["EUR_GBP" "EUR_JPY" "EUR_CHF" "AUD_JPY" "CHF_JPY" "EUR_CAD" "CAD_CHF"])
  (def granularities ["H1" "H1" "H1" "H1" "H1"])
  (def account-ids ["101-001-5729740-001" "101-001-5729740-002" "101-001-5729740-003"
                    "101-001-5729740-004" "101-001-5729740-005"])
  (run-multi-wrapped-rindieses instruments granularities account-ids xindy-config pop-config ga-config)


  ;; (def instruments ["EUR_USD" "USD_JPY" "EUR_GBP" "AUD_USD"
  ;;                   "EUR_JPY" "GBP_USD" "USD_CHF" "AUD_JPY"
  ;;                   "USD_CAD" "CHF_JPY" "EUR_CHF" "CAD_CHF"
  ;;                   "NZD_USD" "EUR_CAD" "AUD_CHF" "CAD_JPY"])
  ;; (def granularities ["M4" "M5" "M10" "M15" "M30" "H1" "H2"])
  ;; (def account-ids ["101-001-5729740-001" "101-001-5729740-002" "101-001-5729740-003"
  ;;                   "101-001-5729740-004" "101-001-5729740-005" "101-001-5729740-006"
  ;;                   "101-001-5729740-007"])

  ;; end comment
  )

(comment
  (def xindy-config (config/get-xindy-config 16 1000))
  (def pop-config (ga/xindy-pop-config 300 80 0.5 0.5))
  (def ga-config (ga/xindy-ga-config 25 25000 0.95))
  (def granularity "S15")

  (def wrapped-rindieses (get-wrapped-rindieses
                          ["EUR_USD"]
                          xindy-config pop-config granularity ga-config))

  ;; (def wrapped-rindieses (get-wrapped-rindieses
  ;;                         ["EUR_USD" "USD_JPY" "EUR_GBP" "AUD_USD" "EUR_JPY"
  ;;                          "GBP_USD" "USD_CHF" "AUD_JPY" "USD_CAD" "CHF_JPY"
  ;;                          "EUR_CHF" "CAD_CHF" "NZD_USD" "EUR_CAD" "AUD_CHF" "CAD_JPY"]
  ;;                         xindy-config pop-config granularity ga-config))

  (map #(list (-> wrapped-rindieses (nth %) :instrument) (-> wrapped-rindieses (nth %) :rindies count)) (range (count wrapped-rindieses)))

  (def filtered-rindieses (filter #(> (-> % :rindies count) 1) wrapped-rindieses))

  (map #(list (-> filtered-rindieses (nth %) :instrument) (-> filtered-rindieses (nth %) :rindies count)) (range (count filtered-rindieses)))

  (run-wrapped-rindieses filtered-rindieses xindy-config granularity "101-001-5729740-001"))

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





