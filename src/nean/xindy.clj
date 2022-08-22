(ns nean.xindy
  (:require [clojure.core.async :as async]
            [config :as config]
            [helpers :as hlp]
            [stats :as stats]
            [uncomplicate.fluokitten.core :refer [fmap]]
            [uncomplicate.neanderthal.core :refer :all]
            [uncomplicate.neanderthal.native :refer :all]
            [util :as util]
            [v0_2_X.plot :as plot]
            [v0_2_X.streams :as streams]))

(defn br []
  (util/bounded-rand 1 -1))

(def nean-grt (fn [x y] (->> (- x y) (* -1E10) Math/exp (+ 1) (/ 1) (* -2) (+ 1))))

;; (def x (dv [1 2 3]))
;; (def y (dv [1 2 3]))
;; (def z (dv [1 2 3]))

;; (defn defns [var-names streams]
;;   (map-indexed
;;    (list 'def var-name stream)))

(defn get-axindy
  ([input-chars min-depth max-depth] (get-axindy 0 input-chars min-depth max-depth))
  ([depth input-chars min-depth max-depth]
   (if
    (or (< depth min-depth) (and (hlp/rand-bool) (<= depth (dec max-depth))))
     (list (br) (get-axindy (inc depth) input-chars min-depth max-depth)
           (br) (get-axindy (inc depth) input-chars min-depth max-depth))
     (-> input-chars rand-nth))))

(defn get-xindy
  ([input-chars min-depth max-depth] (get-xindy 0 input-chars min-depth max-depth))
  ([depth input-chars min-depth max-depth]
   (if
    (or (< depth min-depth) (and (hlp/rand-bool) (<= depth (dec max-depth))))
     (list (get-xindy (inc depth) input-chars min-depth max-depth)
           (get-xindy (inc depth) input-chars min-depth max-depth))
     (-> input-chars rand-nth))))

(defn expand-axindy [form]
  (if (or (= (type form) clojure.lang.Symbol) (= (type form) clojure.lang.Keyword))
    form
    (list 'axpy (nth form 0)
          (expand-axindy (nth form 1))
          (nth form 2)
          (expand-axindy (nth form 3)))))

(defn expand-xindy [form]
  (if (or (= (type form) clojure.lang.Symbol) (= (type form) clojure.lang.Keyword))
    form
    (list 'xpy (expand-xindy (nth form 0))
          (expand-xindy (nth form 1)))))

(defn streams->open-stream
  "Takes streams from streams/fetch-formatted-streams"
  [streams]
  (->> streams :inception-streams first (mapv :o)))

(defn qualified->simple [symb]
  (-> symb str (clojure.string/split #"/") last symbol))

(defn get-simple-xindy [input-chars]
  `(xpy ~@input-chars))

(defn get-rand-shifts [_num max-shift]
  (vec (take _num (repeatedly #(rand-int max-shift)))))

(defn get-populated-xindy [input-shifts stream-name stream-len]
  (let [num-inputs-per (int (/ (count input-shifts) 2))
        input-chars (util/mapv-indexed (fn [ind _] (-> ind (+ 97) char str symbol)) input-shifts)
        form `(let [~input-chars
                    [~@(map
                        (fn [shift] `(subvector ~stream-name ~shift ~stream-len))
                        input-shifts)]]
                (axpy 100 ~(get-simple-xindy (subvec input-chars 0 num-inputs-per))
                      -100 ~(get-simple-xindy (subvec input-chars num-inputs-per))))]
    {:input-shifts input-shifts :form form :sieve (-> form eval)}))

(defn dv-stream>delta [stream]
  (let [stream-len-1 (- (dim stream) 1)]
    (axpy -1 (subvector stream 0 stream-len-1) (subvector stream 1 stream-len-1))))

(defn dv-sieve->rivulet [sieve intention-delta]
  (fmap * (subvector sieve 0 (- (dim sieve) 1)) intention-delta))

(defn dv-sieve-intention->rivulet [sieve intention-stream]
  (let [intention-delta (dv-stream>delta intention-stream)]
    (dv-sieve->rivulet sieve intention-delta)))

(defn get-hyxindy [populated-xindy intention-stream-dv]
  (let [rivulet (dv-sieve-intention->rivulet (get populated-xindy :sieve) intention-stream-dv)]
    ;; (assoc populated-xindy :rivulet rivulet :beck (reductions + (vec (seq rivulet))) :score (stats/score-x (seq rivulet)))))
    (assoc populated-xindy :rivulet rivulet :score (stats/score-x (seq rivulet)))))

(defn in-range [val range-low range-high]
  (and (>= val range-low) (<= val range-high)))

(defn modify-input-shifts [input-shifts max-shift]
  (mapv
   (fn [shift]
     (let [new-shift (-> 41 rand-int (- 20) (+ shift))]
       (if (in-range new-shift 0 max-shift) new-shift shift)))
   input-shifts))

(defn improve-hyxindy
  ([hyxindy stream-dv stream-name max-shift] (improve-hyxindy hyxindy stream-dv stream-name max-shift false))
  ([hyxindy stream-dv stream-name max-shift with-plotting?]
   (let [stream-len (dim stream-dv)
         new-shifts (modify-input-shifts (:input-shifts hyxindy) max-shift)
         new-hyxindy (get-hyxindy (get-populated-xindy new-shifts stream-name (- stream-len max-shift)) (subvector stream-dv max-shift (- stream-len max-shift)))]
     (if (> (:score new-hyxindy) (:score hyxindy))
       (do
         (when with-plotting? (plot/plot-streams [(:beck new-hyxindy) (plot/zero-stream (subvec (vec (seq stream-dv)) max-shift))]))
         new-hyxindy)
       hyxindy))))

(defn get-fore-hyx [hyxindy fore-stream-dv fore-stream-name max-shift]
  (let [populated-fore-xindy (get-populated-xindy
                              (:input-shifts hyxindy)
                              fore-stream-name
                              (- (dim fore-stream-dv) max-shift))]
    (get-hyxindy populated-fore-xindy (subvector fore-stream-dv max-shift (- (dim fore-stream-dv) max-shift)))))

(defn get-robustness [back-hyx fore-hyx]
  (stats/z-score (:rivulet back-hyx) (:rivulet fore-hyx)))

(defn combine-back-fore-hyxs [back-hyx fore-hyx]
  (assoc
   (dissoc back-hyx :sieve :rivulet :beck :score)
   :back (dissoc back-hyx :input-shifts :form)
   :fore (dissoc fore-hyx :input-shifts :form)))

(defn big-thing []
  '(do
     (def stream-len 4000)
     (def half-stream-len (int (/ stream-len 2)))
     (def max-shift 100)
     (def backtest-config (config/get-backtest-config-util
                           ["EUR_USD" "both"]
                           "ternary" 1 2 3 stream-len "H1"))
     (def open-stream (streams->open-stream (streams/fetch-formatted-streams backtest-config)))
     (def back-open-stream (subvec open-stream 0 half-stream-len))
     (def fore-open-stream (subvec open-stream (- half-stream-len max-shift)))
     (def open-stream-dv (dv open-stream))
     (def back-open-stream-dv (dv back-open-stream))
     (def fore-open-stream-dv (dv fore-open-stream))
     (loop [i 0 robust-hyxs []]
       (let [input-shifts (get-rand-shifts 8 max-shift)
             populated-xindy (get-populated-xindy input-shifts 'back-open-stream-dv (- half-stream-len max-shift))
             hyxindy (get-hyxindy populated-xindy (subvector back-open-stream-dv max-shift (- (dim back-open-stream-dv) max-shift)))
             best-hyx (loop [j 0 hyx hyxindy]
                        (if (>= j 50) hyx
                            (recur (inc j)
                                   (improve-hyxindy hyx back-open-stream-dv 'back-open-stream-dv max-shift))))
             fore-hyx (get-fore-hyx best-hyx fore-open-stream-dv 'fore-open-stream-dv max-shift)
             robustness (stats/z-score (seq (:rivulet best-hyx)) (seq (:rivulet fore-hyx)))
             foo (println i robustness)]
         (if (>= i 100) robust-hyxs
             (recur (inc i) (if (> robustness 0) (conj robust-hyxs (combine-back-fore-hyxs best-hyx fore-hyx)) robust-hyxs)))))))

(comment

  (def hyxs (eval (big-thing)))

  (plot/plot-streams [(vec (concat (:beck (:back (first hyxs))) (:beck (:fore (first hyxs)))))])
  (plot/plot-streams (mapv
                      (fn [ind] (vec (concat (reductions + (vec (seq (:rivulet (:back (nth hyxs ind))))))
                                             (reductions + (vec (seq (:rivulet (:fore (nth hyxs ind)))))))))
                      (range (count hyxs))))


  "Fully Async Multi-currency scheduled runner"
  (let [gran "M5"
        schedule-chan (async/chan)
        future-times (util/get-future-unix-times-sec gran)]

    (util/put-future-times schedule-chan future-times)

    (async/go-loop []
      (when-some [val (async/<! schedule-chan)]
        (doseq [instrument ["EUR_USD" "USD_JPY" "EUR_GBP" "AUD_USD" "EUR_JPY" "GBP_USD"
                            "USD_CHF" "AUD_JPY" "USD_CAD" "ZAR_JPY" "CHF_JPY" "EUR_CHF"
                            "NZD_USD" "EUR_CAD" "NZD_JPY" "AUD_CHF" "CAD_JPY" "CAD_CHF"]]
        ;; (doseq [instrument ["AUD_USD" "EUR_USD" "EUR_AUD"]]
          (async/go
            (let [factory-config (apply config/get-factory-config-util
                                        [[[instrument "both"]
                                          "ternary" 1 2 3 100 1000 gran "score-x"]
                                         [10 0.4 0.1 0.5]
                                         2 400])
                  factory-chan (async/chan)]
              (factory/run-factory-async factory-config factory-chan)
              (arena/run-best-gausts-async factory-chan)
              ;; (arena/get-robustness-async factory-chan)
              ))))
      (when (not (env/get-env-data :KILL_GO_BLOCKS?)) (recur))))


  ;; comment end 
  )

(comment
  (do
    (def stream-len 4000)
    (def max-shift 100)

    (def backtest-config (config/get-backtest-config-util
                          ["EUR_USD" "both"]
                          "ternary" 1 2 3 stream-len "H1"))

    (def open-stream (streams->open-stream (streams/fetch-formatted-streams backtest-config)))

    (def back-open-stream (subvec open-stream 0 (int (/ stream-len 2))))

    (def fore-open-stream (subvec open-stream (int (/ stream-len 2))))

    (def open-stream-dv (dv open-stream))
    (def back-open-stream-dv (dv back-open-stream))
    (def fore-open-stream-dv (dv fore-open-stream))

    (def input-shifts (get-rand-shifts 8 max-shift))

    (def populated-xindy (get-populated-xindy input-shifts (- stream-len max-shift)))

    (def hyxindy (get-hyxindy populated-xindy (subvec open-stream max-shift)))

    ;; (plot/plot-streams [(:beck hyxindy) (plot/zero-stream (subvec open-stream max-shift))])

    (def best-hyx (loop [i 0 hyx hyxindy] (if (>= i 2000) hyx (recur (inc i) (improve-hyxindy hyx open-stream stream-len max-shift))))))


  ;; comment end 
  )

(comment
  (def backtest-config (config/get-backtest-config-util
                        ["EUR_USD" "both"]
                        "ternary" 1 2 3 4000 "H1"))

  (def open-stream-dv (dv (streams->open-stream (streams/fetch-formatted-streams backtest-config))))

  (def aaxindy '(0.6176727490832976
                 a
                 -0.11755608865794187
                 (0.7371670008498643 b -0.8446439492317692 a)))

  (get-axindy '[a b c d] 2 3)

  (expand-axindy aaxindy)

  (let [input-shifts (vec (take 5 (repeatedly #(rand-int 50))))
        input-chars (util/mapv-indexed (fn [ind _] (-> ind (+ 97) char str symbol)) input-shifts)
        form `(let [~input-chars
                    [~@(map
                        (fn [item] `(subvector open-stream-dv ~item 150))
                        input-shifts)]]
                ~(expand-axindy (get-axindy input-chars 3 4)))]
    form)

  (defn get-simple-xindy [input-chars]
    `(xpy ~@input-chars))

  (let [num-inputs-per 2
        input-shifts (vec (take (* 2 num-inputs-per) (repeatedly #(rand-int 50))))
        input-chars (util/mapv-indexed (fn [ind _] (-> ind (+ 97) char str symbol)) input-shifts)
        form `(let [~input-chars
                    [~@(map
                        (fn [item] `(subvector open-stream-dv ~item 3950))
                        input-shifts)]]
                (fmap nean-grt
                      ~(get-simple-xindy (subvec input-chars 0 num-inputs-per))
                      ~(get-simple-xindy (subvec input-chars num-inputs-per))))]
    form)

  (let [input-shifts (vec (take 5 (repeatedly #(rand-int 50))))
        input-chars (util/mapv-indexed (fn [ind _] (-> ind (+ 97) char str symbol)) input-shifts)
        form `(let [~input-chars
                    [~@(map
                        (fn [item] `(subvector open-stream-dv ~item 150))
                        input-shifts)]]
                ~(expand-xindy (get-xindy input-chars 3 4)))]
    form)

  `(let [~(qualified->simple ::a) (subvector open-stream-dv ~(rand-int 10) 10)
         ~(qualified->simple ::b) (subvector open-stream-dv ~(rand-int 10) 10)]
     ~(expand-axindy aaxindy))

  ;; (solve-axindy aaxindy open-stream-dv 10)


  ;; end of comment
  )

(comment

  (defn formatted-streams->stream
    "Takes formatted streams from streams/fetch-formatted-streams
   which is a map of keys :inception-streams and :intention-streams"
    [streams _key]
    (->> streams :inception-streams first (mapv _key)))


  (def backtest-config (config/get-backtest-config-util
                        ["EUR_USD" "both"]
                        "ternary" 1 2 3 100 "H4"))

  (def streams (streams/fetch-formatted-streams backtest-config))

  (def o (dv (formatted-streams->stream streams :o)))
  (def h (dv (formatted-streams->stream streams :h)))
  (def l (dv (formatted-streams->stream streams :l)))
  (def c (dv (formatted-streams->stream streams :c)))

  (let [expression (macroexpand
                    '(make-hindy o h l c))
        hydrated (-> expression eval seq)]
    {:expression expression :hydrated hydrated})

  (make-hindy
   (dv (formatted-streams->stream streams :o))
   (dv (formatted-streams->stream streams :h))
   (dv (formatted-streams->stream streams :l))
   (dv (formatted-streams->stream streams :c))))


