(ns nean.xindy2
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
            [v0_2_X.streams :as streams]))

(defn br []
  (util/bounded-rand 1 -1))

(defn streams->open-stream
  "Takes streams from streams/fetch-formatted-streams"
  [streams]
  (->> streams :inception-streams first (mapv :o)))

(defn get-rand-shifts [_num max-shift]
  (vec (take _num (repeatedly #(+ 1 (rand-int (- max-shift 1)))))))

(defn sort-shift-halves [shifts]
  (let [halves (split-at (int (/ (count shifts) 2)) shifts)]
    (vec (concat (sort (first halves)) (sort (second halves))))))

(defn get-subvecs [shifts max-shift dv-stream]
  (for [shift shifts]
    (subvector dv-stream shift (- (dim dv-stream) max-shift))))

(defn shifts->sieve [shifts max-shift stream]
  (let [mag (if (> (first stream) 10) 1 100)
        subvecs (get-subvecs shifts max-shift stream)
        halves (split-at (int (/ (count shifts) 2)) subvecs)]
    (axpy mag (apply xpy (first halves)) (* -1 mag) (apply xpy (second halves)))))

(defn stream->delta [stream]
  (let [stream-len-1 (- (dim stream) 1)]
    (axpy -1 (subvector stream 0 stream-len-1) (subvector stream 1 stream-len-1))))

(defn sieve->rivulet [sieve delta]
  (fmap * (subvector sieve 0 (- (dim sieve) 1)) delta))

(defn sieve+stream->rivulet [sieve stream]
  (let [delta (stream->delta stream)]
    (sieve->rivulet sieve delta)))

(defn get-xindy-from-shifts [shifts max-shift stream]
  (let [sieve (shifts->sieve shifts max-shift stream)
        rivulet (sieve+stream->rivulet sieve stream)]
    {:shifts shifts :last-sieve-val (-> sieve seq last) :rivulet rivulet :score (stats/score-x (-> rivulet seq vec))}))

(defn get-rand-xindy
  ([xindy-config stream]
   (let [shifts (sort-shift-halves (get-rand-shifts (:num-shifts xindy-config) (:max-shift xindy-config)))]
     (get-xindy-from-shifts shifts (:max-shift xindy-config) stream))))

(defn get-back-fore-streams [instrument granularity stream-count back-pct max-shift]
  (println "getting: " instrument)
  (let [big-stream (dv (streams/get-big-stream instrument granularity stream-count (min 1000 stream-count)))
        back-len (int (* (dim big-stream) back-pct))
        fore-len (- (dim big-stream) back-len)
        back-stream (subvector big-stream 0 back-len)
        fore-stream (subvector
                     big-stream
                     (- back-len max-shift)
                     (+ fore-len max-shift))]
    {:back-stream back-stream :fore-stream fore-stream}))

(defn num-weekend-bars [granularity]
  (let [secs-per-bar (util/granularity->seconds granularity)
        secs-per-weekend (* 60 60 24 2)]
    (int (/ secs-per-weekend secs-per-bar))))

(defn shifts->xindies
  "shifts is a vector of shift-vectors. each shift-vector has :num-shifts shifts (ints)"
  [instrument shifts xindy-config granularity]
  (let [new-stream (dv (streams/get-big-stream
                        instrument
                        granularity (+ 2 (num-weekend-bars granularity) (:max-shift xindy-config))))]
    (for [shift-vec shifts]
      (get-xindy-from-shifts shift-vec (:max-shift xindy-config) new-stream))))
