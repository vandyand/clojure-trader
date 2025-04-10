(ns nean.xindy
  (:require [api.oanda_api :as oa]
            [stats :as stats]
            [util :as util]))

(defn get-rand-shifts [_num max-shift]
  (vec (take _num (repeatedly #(+ 1 (rand-int (- max-shift 1)))))))

(defn sort-shift-halves [shifts]
  (let [halves (split-at (int (/ (count shifts) 2)) shifts)]
    (vec (concat (sort (first halves)) (sort (second halves))))))

(defn get-subvecs [shifts max-shift stream]
  (for [shift shifts]
    (subvec stream (- max-shift shift) (- (count stream) shift))))

(defn axpy
  "Performs the operation alpha * x + beta * y for vectors x and y.
  Supports multiple arities:
  - (axpy x y) adds vectors x and y element-wise.
  - (axpy alpha x y) multiplies vector x by alpha and adds it to vector y.
  - (axpy alpha x beta y) multiplies vector x by alpha, vector y by beta, and adds the results."
  ([x y]
   (mapv + x y))

  ([alpha x y]
   (mapv #(+ (* alpha %1) %2) x y))

  ([alpha x beta y]
   (mapv #(+ (* alpha %1) (* beta %2)) x y)))

(defn xpy [& vecs]
  (reduce (fn [acc v] (mapv + acc v)) vecs))

(defn shifts->sieve [shifts max-shift stream]
  (let [mag (if (> (first stream) 10) 1 100)
        subvecs (get-subvecs shifts max-shift stream)
        halves (split-at (int (/ (count shifts) 2)) subvecs)]
    (axpy mag (apply xpy (first halves)) (* -1 mag) (apply xpy (second halves)))))

(defn stream->delta [stream]
  (let [stream-len-1 (- (count stream) 1)]
    (axpy -1 (subvec stream 0 stream-len-1) (subvec stream 1 stream-len-1))))

(defn sieve->rivulet [sieve delta]
  (map * (subvec sieve 0 (- (count sieve) 1)) delta))

(defn sieve+stream->rivulet [sieve stream]
  (let [delta (stream->delta stream)]
    (sieve->rivulet sieve delta)))

(defn get-xindy-from-shifts [shifts max-shift stream]
  (let [sieve (shifts->sieve shifts max-shift stream)
        sieve-mean (stats/mean sieve)
        sieve-stdev (stats/stdev sieve)
        last-sieve-val (-> sieve seq last)
        last-rel-sieve-val (if (not= sieve-stdev 0.0)
                             (/ (- last-sieve-val sieve-mean) sieve-stdev)
                             0.0)
        rivulet (sieve+stream->rivulet sieve stream)]
    {:shifts shifts
     :last-sieve-val last-sieve-val
     :last-rel-sieve-val last-rel-sieve-val
     :rivulet rivulet
     :ga-score (stats/score-x (-> rivulet seq vec))}))

(defn get-rand-xindy
  ([xindy-config stream]
   (let [shifts (sort-shift-halves (get-rand-shifts (:num-shifts xindy-config) (:max-shift xindy-config)))]
     (get-xindy-from-shifts shifts (:max-shift xindy-config) stream))))

(defn get-from-to-times
  ([granularity _count] (get-from-to-times granularity _count 5000))
  ([granularity _count span]
   (let [from-time (util/get-past-unix-time granularity _count)
         to-time (util/current-time-sec)
         time-span (* span (util/granularity->seconds granularity))]
     (partition
      2 1
      (loop [val to-time vals []]
        (if (<= val from-time)
          (conj vals from-time)
          (recur (- val time-span) (conj vals val))))))))

(defn get-big-stream-old
  ([instrument granularity _count] (get-big-stream-old instrument granularity _count 1000))
  ([instrument granularity _count span]
   (let [from-to-times (get-from-to-times granularity (* 2 _count) span)]
     (loop [i 0 stream []]
       (let [from-to-time (-> from-to-times (nth i))
             from-time (second from-to-time)
             to-time (first from-to-time)
             stream-config {:name instrument
                            :granularity granularity
                            :from from-time
                            :to to-time
                            :includeFirst false
                            :count _count}
             new-stream-section (oa/get-instrument-stream stream-config)
             new-stream (into new-stream-section stream)]
         (if (or (>= i (-> from-to-times count dec)) (>= (count new-stream) _count))
           (mapv :o new-stream)
           (recur (inc i) new-stream)))))))

(defn get-big-stream
  [instrument granularity _count]
  (let [stream-config {:name instrument
                       :granularity granularity
                       :count _count
                      ;;  :to "1717704000.000000000"
                      ;;  :from (str (- 1717704000 (* 60 60 5000)) ".000000000")
                       }
        stream (oa/get-instrument-stream stream-config)]
    (mapv :o stream)))

;; (def big-stream (get-big-stream "EUR_USD", "H1", 7777))
;; (count big-stream)
;; (first big-stream)
;; (second big-stream)
;; (last big-stream)

(defn subvec-end [vs target-len]
  (if (> target-len (count vs))
    (throw (IllegalArgumentException. "target-len is greater than the length of the vector"))
    (subvec vs (- (count vs) target-len))))

(defn get-stream
  [instrument granularity _count]
  (subvec-end (get-big-stream instrument granularity _count) _count))

(comment
  (def eth_stream (get-big-stream "ETHUSDT" "H1" 12))
  (println eth_stream)
  (def eur_stream (get-big-stream "EUR_USD" "H1" 12))
  (println eur_stream))

(defn get-back-fore-streams [instrument granularity stream-count back-pct max-shift]
  (let [big-stream (vec (get-big-stream instrument granularity (+ stream-count max-shift)))
        _ (println "big-stream count: " (count big-stream))
        back-len (int (* (count big-stream) back-pct))
        fore-len (- (count big-stream) back-len)
        back-stream (subvec big-stream 0 back-len)
        fore-stream (subvec
                     big-stream
                     (- back-len max-shift)
                     (count big-stream))]
    {:back-stream back-stream :fore-stream fore-stream :total-stream big-stream}))

;; (def streams (get-back-fore-streams "EUR_USD", "H1", 7777, 0.9, 777))

;; (println (count (:back-stream streams)))
;; (println (keys streams))

(defn num-weekend-bars [granularity]
  (let [secs-per-bar (util/granularity->seconds granularity)
        secs-per-weekend (* 60 60 24 2)]
    (int (/ secs-per-weekend secs-per-bar))))

(defn shifts->xindies
  "shifts is a vector of shift-vectors. each shift-vector has :num-shifts shifts (ints)"
  [instrument shifts xindy-config granularity]
  (let [new-stream (vec (get-big-stream
                         instrument
                         granularity (+ 2 (num-weekend-bars granularity) (:max-shift xindy-config))))]
    (for [shift-vec shifts]
      (get-xindy-from-shifts shift-vec (:max-shift xindy-config) new-stream))))
