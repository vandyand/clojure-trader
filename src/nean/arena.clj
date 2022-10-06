(ns nean.arena
  (:require [api.oanda_api :as oapi]
            [clojure.core.async :as async]
            [config :as config]
            [env :as env]
            [file :as file]
            [nean.ga :as ga]
            [nean.xindy2 :as x2]
            [stats :as stats]
            [uncomplicate.neanderthal.core :refer :all]
            [uncomplicate.neanderthal.native :refer :all]
            [util :as util]
            [v0_2_X.streams :as streams]
            [v0_3_X.arena :as arena]))

(comment
  "strindy = strategy + indicator(s)
   xindy = xpy strindy
   rindy = robust xindy (fore performance is 'as good as' back performance)
   rindies = robust xindies
   wrindies = wrapped robust xindies (map with keys :instrument :rindy-shiftss)
   wrindieses = vector of wrindies")

(defn get-robustness [back-xindy fore-xindy]
  (stats/z-score (-> back-xindy :rivulet seq) (-> fore-xindy :rivulet seq)))

(defn combine-xindy [back-xindy fore-xindy]
  {:back back-xindy :fore fore-xindy :robustness (get-robustness back-xindy fore-xindy)})

(defn combine-xindies [back-xindies fore-xindies]
  (map combine-xindy back-xindies fore-xindies))

(defn get-rindies-shiftss [num-generations pop-config xindy-config back-stream fore-stream]
  (let [best-xindies (ga/get-parents (ga/run-generations num-generations pop-config xindy-config back-stream) pop-config)
        fore-xindies (for [xindy best-xindies]
                       (x2/get-xindy-from-shifts (:shifts xindy) (:max-shift xindy-config) fore-stream))
        full-xindies (combine-xindies best-xindies fore-xindies)
        rindies (filter #(and (> (-> % :back :score) 0) (> (-> % :fore :score) 0) (> (:robustness %) -0.25)) full-xindies)]
    (println "num rindies:" (count rindies))
    (map #(-> % :back :shifts) rindies)))

(defn get-wrindies [instrument xindy-config pop-config granularity ga-config]
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
     :rindy-shiftss (get-rindies-shiftss (:num-generations ga-config) pop-config xindy-config back-stream fore-stream)}))

(defn consolidate-wrindieses
  "If there are multiple wrindies of the same instrument in wrindieses
   this function consolidates them (combines all the like-instrument rindies
   into one wrindies per instrument)"
  [wrindieses]
  (let [unique-instruments (set (map :instrument wrindieses))]
    (for [instrument unique-instruments]
      (let [instrument-wrindieses (filter #(= (:instrument %) instrument) wrindieses)] {:instrument instrument
                                                                                        :rindy-shiftss (map :rindy-shiftss instrument-wrindieses)}))))

(defn get-wrindieses
  ([i xc pc g gc] (get-wrindieses i xc pc g gc 1))
  ([instruments xindy-config pop-config granularity ga-config instrument-frequency]
   (let [instrumentss (flatten (repeat instrument-frequency instruments))
         wrindieses (for [instrument instrumentss]
                      (get-wrindies instrument xindy-config pop-config granularity ga-config))]
     (if (= (count (map :instruments wrindieses)) (count (set (map :instruments wrindieses))))
       (list wrindieses)
       (consolidate-wrindieses wrindieses)))))

(defn num-weekend-bars [granularity]
  (let [secs-per-bar (util/granularity->seconds granularity)
        secs-per-weekend (* 60 60 24 2)]
    (int (/ secs-per-weekend secs-per-bar))))

(defn get-new-xindieses-from-wrindies [wrindies xindy-config granularity]
  (let [new-stream (dv (streams/get-big-stream
                        (:instrument wrindies)
                        granularity (+ 10 (num-weekend-bars granularity) (* 2 (:max-shift xindy-config)))))]
    (for [rindy-shiftss (:rindy-shiftss wrindies)]
      (for [shifts rindy-shiftss]
        (x2/get-xindy-from-shifts shifts (:max-shift xindy-config) new-stream)))))

(defn get-position-from-xindieses [xindieses account-id]
  (let [account-balance (oapi/get-account-balance account-id)
        max-pos (int (* 1.0 account-balance))
        target-pos (int
                    (+ 0.5
                       (* 0.125 account-balance
                          (stats/mean
                           (for [xindies xindieses]
                             (stats/mean (map #(-> % :sieve seq last) xindies)))))))]
    (cond
      (> target-pos max-pos) max-pos
      (< target-pos (* -1 max-pos)) (* -1 max-pos)
      :else target-pos)))

(defn run-wrindieses
  ([wr xc g] (run-wrindieses wr xc g (env/get-account-id)))
  ([wrindieses xindy-config granularity account-id]
   (let [schedule-chan (async/chan)]
     (util/put-future-times schedule-chan (util/get-future-unix-times-sec granularity))
     (async/go-loop []
       (when-some [val (async/<! schedule-chan)]
         (doseq [wrindies wrindieses]
           (async/go
             (arena/post-target-pos
              (:instrument wrindies)
              (get-position-from-xindieses
               (get-new-xindieses-from-wrindies
                wrindies
                xindy-config
                granularity)
               account-id)
              account-id))))
       (when (not (env/get-env-data :KILL_GO_BLOCKS?)) (recur)))
     schedule-chan)))

(defn generate-and-run-wrindieses
  ([i g ai xc pc gc] (generate-and-run-wrindieses i g ai xc pc gc (take (count i) (repeat 1))))
  ([instruments granularities account-ids xindy-config pop-config ga-config instrument-freq]
   (doseq [gran-account-id (partition 2 (interleave granularities account-ids))]
     (async/go
       (let [granularity (first gran-account-id)
             account-id (second gran-account-id)
             wrindieses (get-wrindieses instruments xindy-config pop-config granularity ga-config instrument-freq)]
         (run-wrindieses wrindieses xindy-config granularity account-id))))))

(defn save-wrindieses [file-name wrindieses all-config]
  (file/write-file file-name wrindieses))

(defn get-and-save-wrindieses [file-name & get-wrindieses-args]
  (save-wrindieses file-name (apply get-wrindieses get-wrindieses-args)))



(defn run-wrindieses-from-file
  ([file-name]
   (let [file-content (file/read-file file-name)
         {:keys [granularity wrindieses xindy-config account-id]} file-content
         schedule-chan (async/chan)]
     (util/put-future-times schedule-chan (util/get-future-unix-times-sec granularity))
     (async/go-loop []
       (when-some [val (async/<! schedule-chan)]
         (doseq [wrindies wrindieses]
           (async/go
             (arena/post-target-pos
              (:instrument wrindies)
              (get-position-from-xindieses
               (get-new-xindieses-from-wrindies
                wrindies
                xindy-config
                granularity)
               account-id)
              account-id))))
       (when (not (env/get-env-data :KILL_GO_BLOCKS?)) (recur)))
     schedule-chan)))

(defn generate-and-run-wrindieses
  ([i g ai xc pc gc] (generate-and-run-wrindieses i g ai xc pc gc (take (count i) (repeat 1))))
  ([instruments granularities account-ids xindy-config pop-config ga-config instrument-freq]
   (doseq [gran-account-id (partition 2 (interleave granularities account-ids))]
     (async/go
       (let [granularity (first gran-account-id)
             account-id (second gran-account-id)
             wrindieses (get-wrindieses instruments xindy-config pop-config granularity ga-config instrument-freq)]
         (run-wrindieses wrindieses xindy-config granularity account-id))))))


(comment
  ;; (do
  (def instruments ["EUR_USD" "USD_JPY" "AUD_USD" "GBP_USD" "USD_CHF"])
  (def instruments ["EUR_USD" "AUD_USD"])

  (def instruments ["EUR_USD" "USD_JPY" "EUR_GBP" "AUD_USD"
                    "EUR_JPY" "GBP_USD" "USD_CHF" "AUD_JPY"
                    "USD_CAD" "CHF_JPY" "EUR_CHF" "CAD_CHF"
                    "NZD_USD" "EUR_CAD" "AUD_CHF" "CAD_JPY"])

  (def instruments ["AUD_CAD" "AUD_CHF" "AUD_JPY" "AUD_NZD" "AUD_SGD" "AUD_USD" "CAD_CHF" "CAD_JPY"
                    "CAD_SGD" "CHF_JPY" "CHF_ZAR" "EUR_AUD" "EUR_CAD" "EUR_CHF" "EUR_CZK" "EUR_GBP"
                    "EUR_JPY" "EUR_NZD" "EUR_SEK" "EUR_SGD" "EUR_USD" "EUR_ZAR" "GBP_AUD" "GBP_CAD"
                    "GBP_CHF" "GBP_JPY" "GBP_NZD" "GBP_SGD" "GBP_USD" "GBP_ZAR" "NZD_CAD" "NZD_CHF"
                    "NZD_JPY" "NZD_SGD" "NZD_USD" "SGD_CHF" "SGD_JPY" "USD_CAD" "USD_CHF" "USD_CNH"
                    "USD_CZK" "USD_DKK" "USD_JPY" "USD_SEK" "USD_SGD" "USD_THB" "USD_ZAR" "ZAR_JPY"])

  (def instrument-freq 7)
  (def granularity "H1")
  (def xindy-config (config/get-xindy-config 8 750))
  (def pop-config (ga/xindy-pop-config 150 75))
  (def ga-config (ga/xindy-ga-config 15 20000 0.95))

  (def wrindieses (get-wrindieses instruments xindy-config pop-config granularity ga-config instrument-freq))
  (def wrindieses2 (get-wrindieses instruments xindy-config pop-config granularity ga-config instrument-freq))
  
  (save-wrindieses "data/wrindieses/wrindieses1.edn" wrindieses)
  
  (def all-config (merge {:instruments instruments} xindy-config pop-config {:granularity granularity} ga-config {:instrument-freq instrument-freq}))

  (keys all-config)
  (map str (vals all-config))
  
  (def wrindieses2 (get-wrindieses instruments xindy-config pop-config granularity ga-config instrument-freq))

  (for [wrindies wrindieses]
    (arena/post-target-pos
     (:instrument wrindies)
     (get-position-from-xindieses
      (get-new-xindieses-from-wrindies
       wrindies
       xindy-config
       granularity)
      "101-001-5729740-001")
     "101-001-5729740-001"))

  (run-wrindieses wrindieses xindy-config granularity "101-001-5729740-002")

  (generate-and-run-wrindieses
   instruments ["H1" "H1" "H1"]
   ["101-001-5729740-001"
    "101-001-5729740-002"
    "101-001-5729740-003"] xindy-config
   pop-config ga-config
   instrument-freq)


  ;; end comment
  )

(comment

  (let [granularity "M5"
        account-id "101-001-5729740-001"
        schedule-chan (async/chan)]
    (util/put-future-times schedule-chan (util/get-future-unix-times-sec granularity))
    (async/go-loop []
      (when-some [val (async/<! schedule-chan)]
        (let [instruments ["USD_CHF"]
              xindy-config (config/get-xindy-config 4 250)
              pop-config (ga/xindy-pop-config 50 20)
              ga-config (ga/xindy-ga-config 10 25000 0.95)
              instrument-freq 7
              wrindieses (get-wrindieses instruments xindy-config pop-config granularity ga-config instrument-freq)]
          (doseq [wrindies wrindieses]
            (async/go
              (arena/post-target-pos
               (:instrument wrindies)
               (get-position-from-xindieses
                (get-new-xindieses-from-wrindies
                 wrindies
                 xindy-config
                 granularity)
                account-id)
               account-id)))))
      (when (not (env/get-env-data :KILL_GO_BLOCKS?)) (recur)))
    schedule-chan)

  ;; End Comment
  )


(comment
  (def xindy-config (config/get-xindy-config 6 500))
  (def pop-config (ga/xindy-pop-config 4000 1000))
  (def ga-config (ga/xindy-ga-config 10 100000 0.95))
  (def instruments ["EUR_USD" "USD_JPY" "EUR_JPY"])
  (def instrument-freq 3)
  (def granularities ["M10" "M30" "H2"])
  (def account-ids ["101-001-5729740-004" "101-001-5729740-005" "101-001-5729740-006"])
  (generate-and-run-wrindieses
   instruments granularities
   account-ids xindy-config
   pop-config ga-config
   instrument-freq)


  (def instruments ["EUR_USD" "USD_JPY" "EUR_GBP" "AUD_USD"
                    "EUR_JPY" "GBP_USD" "USD_CHF" "AUD_JPY"
                    "USD_CAD" "CHF_JPY" "EUR_CHF" "CAD_CHF"
                    "NZD_USD" "EUR_CAD" "AUD_CHF" "CAD_JPY"])
  ;; (def granularities ["M4" "M5" "M10" "M15" "M30" "H1" "H2"])
  ;; (def account-ids ["101-001-5729740-001" "101-001-5729740-002" "101-001-5729740-003"
  ;;                   "101-001-5729740-004" "101-001-5729740-005" "101-001-5729740-006"
  ;;                   "101-001-5729740-007"])

  ;; end comment
  )


(comment

  (stats/stdev (streams/get-big-stream "EUR_USD" "M5" 10000))

  ;; End Comment
  )