(ns monitor.monitor
  (:require
   [api.oanda_api :as oapi]
   [util :as util]
   [file :as file]
   [clojure.core.async :as async]
   [env :as env]
   [plot :as plot]))

(defn get-navs [account-ids]
  (for [account-id account-ids]
    (oapi/get-account-nav account-id)))

(defn get-difs [navs]
  (map #(- % 1000) navs))

(defn get-sum [difs]
  (reduce + difs))

(defn shorten-account-id [account-id]
  (-> account-id (clojure.string/split #"-") last))

(defn get-performance [account-ids]
  (let [navs (get-navs account-ids)
        difs (get-difs navs)
        sum (get-sum difs)]
    (assoc (apply hash-map (interleave (map keyword (map shorten-account-id account-ids)) difs))
           :sum sum
           :time (util/current-time-sec))))

(defn get-and-write-performance
  ([account-ids] (get-and-write-performance account-ids "data/performance.edn"))
  ([account-ids file-name] (get-and-write-performance account-ids file-name true))
  ([account-ids file-name pprint?]
   (let [perf (get-performance account-ids)
         foo (when pprint? (clojure.pprint/pprint perf))]
     (file/write-file file-name perf true))))

(defn scheduled-perf-writer [account-ids granularity]
  (let [schedule-chan (async/chan)]
    (util/put-future-times schedule-chan (util/get-future-unix-times-sec granularity))
    (async/go-loop []
      (when-some [val (async/<! schedule-chan)]
        (get-and-write-performance account-ids))
      (when (not (env/get-env-data :KILL_GO_BLOCKS?)) (recur)))))

(defn plot-perf
  ([] (plot-perf "performance.edn"))
  ([file-name]
   (-> file-name (file/read-data-file #"\r\n") plot/format-performance-data plot/generate-and-view-plot)))

(defn scheduled-perf-plotter
  ([] (scheduled-perf-plotter "M1"))
  ([granularity]
   (let [schedule-chan (async/chan)]
     (util/put-future-times schedule-chan (util/get-future-unix-times-sec granularity))
     (async/go-loop []
       (when-some [val (async/<! schedule-chan)]
         (plot-perf))
       (when (not (env/get-env-data :KILL_GO_BLOCKS?)) (recur)))
     schedule-chan)))

(comment

  (plot-perf)
  (def plot-chan (scheduled-perf-plotter))

  (async/close! plot-chan)
  
  ;; end comment
  )

(comment

  (def account-ids ["101-001-5729740-001" "101-001-5729740-002" "101-001-5729740-003"
                    "101-001-5729740-004" "101-001-5729740-005"])

  (get-and-write-performance account-ids)

  (scheduled-perf-writer account-ids "M5")

  ;; end comment
  )

(comment
  (do
    (def account-ids ["101-001-5729740-001" "101-001-5729740-002" "101-001-5729740-003"
                      "101-001-5729740-004" "101-001-5729740-005" "101-001-5729740-006"
                      "101-001-5729740-007"])

    (println
     (reduce
      +
      (util/print-return
       (map
        #(- % 1000)
        (util/print-return
         (for [account-id account-ids]
           (oapi/get-account-nav account-id)))))))


    (def instruments ["EUR_USD" "USD_JPY" "EUR_GBP" "AUD_USD" "EUR_JPY"
                      "GBP_USD" "USD_CHF" "AUD_JPY" "USD_CAD" "CHF_JPY"
                      "EUR_CHF" "CAD_CHF" "NZD_USD" "EUR_CAD" "AUD_CHF" "CAD_JPY"])

    (def
      empty-instus
      (sort-by
       :instrument
       (for [inst instruments]
         {:instrument inst :units 0})))

    (def positions
      (for [account-id account-ids]
        (sort-by :instrument
                 (oapi/get-formatted-open-positions account-id))))

    (reduce
     (fn [acc-instus new-instus]
       (for [instu acc-instus]
         (let [new-instu (let [potential-instu
                               (filter #(= (:instrument %) (:instrument instu)) new-instus)]
                           (if (empty? potential-instu) {:instrument instu :units 0}
                               (first potential-instu)))]
           {:instrument (:instrument instu) :units (+ (:units new-instu) (:units instu))})))
     empty-instus
     positions))

  ;; end of comment
  )