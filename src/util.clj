(ns util)

(defn find-in [coll _key _val] 
  (reduce (fn [_ cur-val] (when (= (_key cur-val) _val) (reduced cur-val)))
        nil coll))

(defn subvec-end [v cnt]
  (if (> cnt -1)
    (subvec v (- (count v) cnt))
    v))

(defn get-overlap-ind [old new]
  (loop [i 0]
    (cond
      (>= i (count new)) -1
      (let [sub-new (subvec new 0 (- (count new) i))
            sub-old (subvec old (- (count old) (count sub-new)))]
        (= sub-old sub-new))
      i
      :else (recur (inc i)))))

(defn current-time-sec []
  (quot (System/currentTimeMillis) 1000))

;; supports these types of granularities https://developer.oanda.com/rest-live-v20/instrument-df/#CandlestickGranularity
(defn granularity->seconds [granularity]
  (let [time-frame (subs granularity 0 1)
        amount-str (subs granularity 1 (count granularity))
        amount (if (= amount-str "") nil (Integer/parseInt amount-str))]
    (cond
      (= "S" time-frame) amount
      (and amount (= "M" time-frame)) (* amount 60)
      (= "H" time-frame) (* amount 60 60)
      (= "D" time-frame) (* 60 60 24)
      (= "W" time-frame) (* 60 60 24 7)
      (= "M" time-frame) (* 60 60 24 7 31))))