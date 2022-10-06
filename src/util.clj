(ns util
  (:require
   [clojure.core.async :as async]))

(defn pos-or-zero [num] (if (pos? num) num 0))

(defn bool->binary [bool]
  (get {true 1 false 0} bool))

(defn find-in [coll _key _val]
  (reduce (fn [_ cur-val] (when (= (_key cur-val) _val) (reduced cur-val)))
          nil coll))

(defn subvec-end [v cnt]
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

(defn round-dub
  "Round a double to the given precision (number of significant digits)"
  [dub precision]
  (let [factor (Math/pow 10 precision)]
    (/ (Math/round (* dub factor)) factor)))

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
  ([granularity] (get-future-unix-times-sec granularity 10000))
  ([granularity _count]
   (let [start-midnight 1653278400]
     (loop [check-time start-midnight v (transient [])]
       (if (>= (count v) _count) (persistent! v)
           (let [new-time (+ check-time (granularity->seconds granularity))]
             (if (> check-time (current-time-sec))
               (recur new-time (conj! v check-time))
               (recur new-time v))))))))

(defn get-past-unix-time [granularity _count]
  (let [cur-time (current-time-sec)
        seconds-per-gran (granularity->seconds granularity)]
    (- cur-time (* seconds-per-gran _count))))

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

(defn rand-caps-str
  ([] (rand-caps-str 4))
  ([len]
   (apply str (take len (repeatedly #(char (+ (rand 26) 65)))))))

(defn rivulet->beck [rivulet]
  (vec (reductions + rivulet))
  ;; (reduce (fn [acc newVal] (conj acc (+ newVal (or (last acc) 0)))) [] rivulet)
  )

(defn bounded-rand [low high]
  (-> (rand) (* (- high low)) (+ low)))

(defn mapv-indexed [f coll]
  (vec (map-indexed f coll)))

(defn print-return [arg]
  (println arg)
  arg)

(defmacro for-do
  "(for seq-exprs (do body-exprs-1 body-exprs-2 etc))"
  [seq-exprs & body-exprs]
  (list 'for seq-exprs (cons 'do body-exprs)))

(defn rand-lin-dist
  "Define a line with x0 (defined as 0), y0; x1, y1
   Function returns random x int value under
   this line, in [x0, x1). y1 defaults to 1 if not
   provided."
  ([y0 x1] (rand-lin-dist y0 x1 1))
  ([y0 x1 y1]
   (let [x (rand x1)
         y (rand (if (> y0 y1) y0 y1))
         m (/ (- y1 y0) x1)]
     (if (< y (-> x (* m) (+ y0)))
       (int x)
       (rand-lin-dist y0 x1 y1)))))

(comment
  (->> #(rand-lin-dist -2 10 2) (repeatedly 100000) frequencies sort))

;------------------------------------;------------------------------------;------------------------------------

(defn put-future-times [chan future-times]
  (async/go-loop
   [v future-times]
    (async/<! (async/timeout 1000))
    (if (= (count v) 0) (async/close! chan)
        (if (< (first v) (current-time-sec))
          (do
            (println "put val on channel: " (first v))
            (async/>! chan (first v))
            (recur (rest v)))
          (recur v)))))

(defn future-times-ons [chan]
  (async/go-loop []
    (async/<! (async/timeout 1000))
    (when-some [val (async/poll! chan)]
      (println "took val from channel: " val))
    (recur)))

(comment
  (do
    (def times-chan (async/chan))

    (def future-times (get-future-unix-times-sec "S2" 4))

    (def put-chan (put-future-times times-chan future-times))

    (def take-chan (future-times-ons times-chan))

    (async/close! times-chan)
    (async/close! put-chan)
    (async/close! take-chan))
  (async/close! times-chan)
  (async/close! put-chan)
  (async/close! take-chan)
  (async/close! times-chan)

  (async/take! times-chan #(println "value is" %)))

;------------------------------------;------------------------------------;------------------------------------

(comment

  (def chan1 (async/chan))

  (def future-times (get-future-unix-times-sec "S5" 4))

  (put-future-times chan1 future-times)

  (async/take! chan1 println)

  ;; end comment
  )
