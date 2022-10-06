(ns stats
  (:require [util :as util]))

(defn mode [vs]
  (let [fs (frequencies vs)]
    (first (last (sort-by second fs)))))

(defn quantile
  ([p vs]
   (let [svs (sort vs)]
     (quantile p (count vs) svs (first svs) (last svs))))
  ([p c svs mn mx]
   (let [pic (* p (inc c))
         k (int pic)
         d (- pic k)
         ndk (if (zero? k) mn (nth svs (dec k)))]
     (cond
       (zero? k) mn
       (= c (dec k)) mx
       (= c k) mx
       :else (+ ndk (* d (- (nth svs k) ndk)))))))

(defn median
  ([vs] (quantile 0.5 vs))
  ([sz svs mn mx] (quantile 0.5 sz svs mn mx)))

(defn mean
  ([vs] (mean (reduce + vs) (count vs)))
  ([vs sz] (if (not= 0 sz) (double (/ vs sz)) 0.0)))

(defn mean-int [vs]
  (int (+ 0.5 (mean vs))))

(defn stdev
  ([vs]
   (stdev vs (count vs) (mean vs)))
  ([vs sz u]
  ;;  (println "stdev: " vs sz u)
   (Math/sqrt (/ (reduce + (map #(Math/pow (- % u) 2) vs))
                 sz))))

(defn median-absolute-deviation
  ([vs]
   (median-absolute-deviation vs (median vs)))
  ([vs m]
   (median (map #(Math/abs (- % m)) vs))))

(defn lower-adjacent-value
  ([vs]
   (let [q1 (quantile 0.25 vs)
         m (median vs)
         q3 (quantile 0.75 vs)]
     (lower-adjacent-value (sort vs) m (- q3 q1))))
  ([svs m qd]
   (let [l (- m qd)]
     (first (filter (partial < l) svs)))))

(defn upper-adjacent-value
  ([vs]
   (let [q1 (quantile 0.25 vs)
         m (median vs)
         q3 (quantile 0.75 vs)]
     (upper-adjacent-value (reverse (sort vs)) m (- q3 q1))))
  ([rsvs m qd]
   (let [l (+ m qd)]
     (first (filter #(< % l) rsvs)))))

(defn stats-map
  ([vs]
   (let [sz (count vs)
         svs (sort vs)
         rsvs (reverse svs)
         mn (first svs)
         mx (first rsvs)
         sm (reduce + vs)
         u (mean sm sz)
         mdn (median sz svs mn mx)
         q1 (quantile 0.25 sz svs mn mx)
         q3 (quantile 0.75 sz svs mn mx)
         sd (stdev vs sz u)
         mad (median-absolute-deviation vs mdn)
         qd (- q3 q1)
         lav (lower-adjacent-value svs mdn qd)
         uav (upper-adjacent-value rsvs mdn qd)]
     {:Size sz
      :Min mn
      :Max mx
      :Mean u
      :Median mdn
      :Mode (mode vs)
      :Q1 q1
      :Q3 q3
      :Total sm
      :SD sd
      :MAD mad
      :LAV lav
      :UAV uav}))
  ([ks vs]
   (zipmap ks (map (stats-map vs) ks))))

(let [ks [:Size :Min :Max :Mean :Median :Mode :Q1 :Q3 :Total :SD :MAD :LAV :UAV]]
  (defn summarise
    ([vs] (summarise "" vs))
    ([label vs]
     (apply format
            (str (reduce #(.append %1 %2)
                         (StringBuilder.)
                         (interpose \tab
                                    ["%1$s::"
                                     "Size: %2$.3f"
                                     "Total: %10$.3f"
                                     "Mean: %5$.3f"
                                     "Mode: %7$.3f"
                                     "Min: %3$.3f"
                                     "LAV: %13$.3f"
                                     "Q1: %8$.3f"
                                     "Median: %6$.3f"
                                     "Q3: %9$.3f"
                                     "UAV: %14$.3f"
                                     "Max: %4$.3f"
                                     "SD: %11$.3f"
                                     "MAD: %12$.3f"])))
            (conj (map (comp double (stats-map vs)) ks) label)))))

(defn closest-mean-fn [means]
  (fn [v] (reduce (partial min-key #(Math/pow (- v %) 2)) means)))

(defn k-means [k vs]
  (let [vs (map double vs)
        svs (set vs)]
    (if (> k (count svs))
      (sort svs)
      (loop [mns (sort (take k (shuffle svs)))
             pmns (repeat k Double/NaN)]
        (if (= mns pmns)
          mns
          (recur (sort (map mean (vals (group-by (closest-mean-fn mns) vs)))) mns))))))

(defn z-score [pop sample]
  (let [x (mean sample) μ (mean pop) n (count sample) σ (stdev pop)]
    (/ (* (- x μ) (Math/sqrt n)) σ)))

(defn balance [vs]
  (reduce + vs))

(defn sharpe [vs]
  (if (<= (count vs) 1) 0.0
      (let [μ (mean vs) σ (stdev vs)]
        (if (= σ 0.0) 0.0 (/ μ σ)))))

(defn max-dd-period
  "Lower is better"
  [vs]
  (if (<= (count vs) 1) 0.0
      (let [beck (util/rivulet->beck vs)]
        (loop [i 0 last-best 0 max-period 0.01 cur-period 0]
          (if (< i (count beck))
            (if (> last-best (nth beck i))
                (recur (inc i) last-best
                       (if (> (inc cur-period) max-period) (inc cur-period) max-period) (inc cur-period))
                (recur (inc i) (nth beck i) max-period 0))
            (double max-period))))))

(defn inv-dd-period [vs]
  (/ 1.0 (max-dd-period vs)))

(defn sharpe-per-std [vs]
  (if (<= (count vs) 1) 0.0
      (let [μ (mean vs) σ (stdev vs)]
        (if (= σ 0.0) 0.0 (/ μ σ σ)))))

(defn score-x
  "values vs should be rivulet"
  [vs]
  (if (<= (count vs) 1) 0.0
      (let [_sharpe (sharpe vs)
            _inv-dd-period (inv-dd-period vs)]
        (* _sharpe _inv-dd-period))))

(defn sum [vs]
  (if (= 0 (count vs))
    0.0
    (apply + vs)))