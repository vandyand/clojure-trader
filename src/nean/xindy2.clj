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
            [v0_2_X.streams :as streams]
            [v0_3_X.arena :as arena]))

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
    {:shifts shifts :sieve sieve :rivulet rivulet :score (stats/score-x (-> rivulet seq vec))}))

(defn get-rand-xindy
  ([xindy-config stream] 
  (let [shifts (sort-shift-halves (get-rand-shifts (:num-shifts xindy-config) (:max-shift xindy-config)))]
    (get-xindy-from-shifts shifts (:max-shift xindy-config) stream))))


(comment

  (def xindy-config (config/get-xindy-config 8 100))

  (def backtest-config (config/get-backtest-config-util
                        ["USD_JPY" "both"]
                        "ternary" 1 2 3 4000 "H1"))

  (def natural-stream (streams->open-stream (streams/fetch-formatted-streams backtest-config)))

  (def stream (dv natural-stream))

  ;; (def sieve (shifts->sieve shifts max-shift stream-dv))

  (def xindy (get-rand-xindy xindy-config stream))

  ;; end comment
  )