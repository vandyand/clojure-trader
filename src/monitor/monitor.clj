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

(defn scheduled-perf-writer
  ([ai g] (scheduled-perf-writer ai g "data/performance.edn"))
  ([account-ids granularity file-name]
   (let [schedule-chan (async/chan)]
     (util/put-future-times schedule-chan (util/get-future-unix-times-sec granularity))
     (async/go-loop []
       (when-some [val (async/<! schedule-chan)]
         (get-and-write-performance account-ids file-name))
       (when (not (env/get-env-data :KILL_GO_BLOCKS?)) (recur))))))

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

(defn print-account-navs [account-ids]
  (println
   (reduce
    +
    (util/print-return
     (map
      #(- % 1000)
      (util/print-return
       (for [account-id account-ids]
         (oapi/get-account-nav account-id))))))))

(defn print-cumulative-positions [account-ids]
  (let [positions (map oapi/get-formatted-open-positions account-ids)
        empty-instus (->> positions flatten (map :instrument) set (map (fn [x] {:instrument x :units 0})))]
    (reduce
     (fn [acc-instus new-instus]
       (for [instu acc-instus]
         (let [potential-instu (first (filter #(= (:instrument %) (:instrument instu)) new-instus))
               new-instu (if potential-instu potential-instu {:instrument (:instrument instu) :units 0})]
           {:instrument (:instrument instu) :units (+ (:units new-instu) (:units instu))})))
     empty-instus
     positions)))

(comment

  (plot-perf)
  (def plot-chan (scheduled-perf-plotter))

  (async/close! plot-chan)

  ;; end comment
  )

(comment
  (def account-ids ["101-001-5729740-007" "101-001-5729740-008" "101-001-5729740-009"])
  (scheduled-perf-writer account-ids "M5" "data/performance3.edn")
  ;; end comment
  )

(comment
  (do
    (def account-ids ["101-001-5729740-001" "101-001-5729740-002" "101-001-5729740-003"])
    (print-account-navs account-ids)
    (print-cumulative-positions account-ids)))