(ns util
  (:require
   [clojure.core.async :as async]))

(defn find-in [coll _key _val]
  (reduce (fn [_ cur-val] (when (= (_key cur-val) _val) (reduced cur-val)))
          nil coll))

(defn subvec-end [v cnt]
  ;; (println "v: " v)
  ;; (println "cnt: " cnt)
  (if (and (> cnt -1) (> (count v) cnt))
    (subvec v (- (count v) cnt))
    v))

(defn get-overlap-ind [old new]
  (if (> (count new) (count old))
    (when (= old (subvec new 0 (count old)))
      (- (count new) (count old)))
    (loop [i 0]
      (cond
        (>= i (count new)) -1
        (let [sub-new (subvec new 0 (- (count new) i))
              sub-old (subvec old (- (count old) (count sub-new)))]
          (= sub-old sub-new))
        i
        :else (recur (inc i))))))

(defn get-fore-ind [proxy new]
  (loop [i 0]
    (when (<= i (- (count new) (count proxy)))
      (let [test-vec (subvec new (- (count new) (count proxy) i) (- (count new) i))]
        (if (= test-vec proxy)
          i
          (recur (inc i)))))))

(defn current-time-sec []
  (quot (System/currentTimeMillis) 1000))

(defn current-time-msec []
  (System/currentTimeMillis))

;; supports these types of granularities https://developer.oanda.com/rest-live-v20/instrument-df/#CandlestickGranularity
(defn granularity->seconds [granularity]
  (let [time-frame (clojure.string/upper-case (subs granularity 0 1))
        amount-str (subs granularity 1 (count granularity))
        amount (if (= amount-str "") nil (Integer/parseInt amount-str))]
    (cond
      (= "S" time-frame) amount
      (and amount (= "M" time-frame)) (* amount 60)
      (= "H" time-frame) (* amount 60 60)
      (= "D" time-frame) (* 60 60 24)
      (= "W" time-frame) (* 60 60 24 7)
      (= "M" time-frame) (* 60 60 24 7 31))))

(defn get-future-unix-times-sec 
  ([granularity] (get-future-unix-times-sec granularity 1000))
  ([granularity _count]
  (let [start-midnight 1653278400]
    (loop [check-time start-midnight v (transient [])]
      (if (>= (count v) _count) (persistent! v)
          (let [new-time (+ check-time (granularity->seconds granularity))]
            (if (> check-time (current-time-sec))
              (recur new-time (conj! v check-time))
              (recur new-time v))))))))

(defn future-times-ons [chan granularity]
  )


(defn find-nested
  [m k]
  (let [rtn-val (->> (tree-seq map? vals m)
       (filter map?)
       (some k))]
    (if rtn-val rtn-val m)))

(defn config->file-name [config]
  (let [backtest-config (find-nested config :backtest-config)]
    (str (clojure.string/join
        "-"
        (conj
          (map
           (fn [stream-conf] (if (= "inception" (get stream-conf :incint))
                               (get stream-conf :name)
                               (str "T_" (get stream-conf :name))))
           (get backtest-config :streams-config))
         (get backtest-config :num-data-points)
         (get backtest-config :granularity)))
       ".edn")))

;------------------------------------;------------------------------------;------------------------------------

(defn put-future-times [chan future-times]
  (async/go-loop
   [v future-times]
    (if (= (count v) 0) nil
     (if (< (first v) (util/current-time-sec))
      (do
        (println "put val on channel: " (first v))
        (async/>! chan (first v))
        (recur (rest v)))
      (recur v)))))

(defn future-times-ons [chan]
  (async/go-loop []
    (when-some [val (async/<! chan)]
      (println "took val from channel: " val))
    (recur)))

(comment
  (do
    (def times-chan (async/chan))

    (def future-times (util/get-future-unix-times-sec "S5" 2))

    (put-future-times times-chan future-times)

    (future-times-ons times-chan))

  (async/close! times-chan)
  )