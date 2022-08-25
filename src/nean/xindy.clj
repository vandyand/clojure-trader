(ns nean.xindy
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
            [v0_2_X.plot :as plot]
            [v0_2_X.streams :as streams]
            [v0_3_X.arena :as arena]))

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

(defn get-populated-xindy [input-shifts stream-name stream-len jpy?]
  (let [num-inputs-per (int (/ (count input-shifts) 2))
        input-chars (util/mapv-indexed (fn [ind _] (-> ind (+ 97) char str symbol)) input-shifts)
        form `(let [~input-chars
                    [~@(map
                        (fn [shift] `(subvector ~stream-name ~shift ~stream-len))
                        input-shifts)]]
                (axpy (if ~jpy? 1 100) ~(get-simple-xindy (subvec input-chars 0 num-inputs-per))
                      (if ~jpy? -1 -100) ~(get-simple-xindy (subvec input-chars num-inputs-per))))]
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
  ([hyxindy stream-dv stream-name max-shift jpy?] (improve-hyxindy hyxindy stream-dv stream-name max-shift jpy? false))
  ([hyxindy stream-dv stream-name max-shift jpy? with-plotting?]
   (let [stream-len (dim stream-dv)
         new-shifts (modify-input-shifts (:input-shifts hyxindy) max-shift)
         new-hyxindy (get-hyxindy (get-populated-xindy new-shifts stream-name (- stream-len max-shift) jpy?) (subvector stream-dv max-shift (- stream-len max-shift)))]
     (if (> (:score new-hyxindy) (:score hyxindy))
       (do
         (when with-plotting? (plot/plot-streams [(:beck new-hyxindy) (plot/zero-stream (subvec (vec (seq stream-dv)) max-shift))]))
         new-hyxindy)
       hyxindy))))

(defn get-fore-hyx [hyxindy fore-stream-dv fore-stream-name max-shift jpy?]
  (let [populated-fore-xindy (get-populated-xindy
                              (:input-shifts hyxindy)
                              fore-stream-name
                              (- (dim fore-stream-dv) max-shift)
                              jpy?)]
    (get-hyxindy populated-fore-xindy (subvector fore-stream-dv max-shift (- (dim fore-stream-dv) max-shift)))))

(defn get-robustness [back-hyx fore-hyx]
  (stats/z-score (:rivulet back-hyx) (:rivulet fore-hyx)))

(defn combine-back-fore-hyxs [back-hyx fore-hyx instrument]
  (assoc
   (dissoc back-hyx :sieve :rivulet :beck :score)
   :back (dissoc back-hyx :input-shifts :form)
   :fore (dissoc fore-hyx :input-shifts :form)
   :instrument instrument))

(defn big-thing [instrument granularity]
  `(do
     (def jpy? (clojure.string/includes? (clojure.string/trim \"~instrument\") "JPY"))
     (def stream-len 4000)
     (def half-stream-len (int (/ stream-len 2)))
     (def max-shift 100)
     (def backtest-config (config/get-backtest-config-util
                           [~instrument "both"]
                           "ternary" 1 2 3 stream-len ~granularity))
     (def open-stream (streams->open-stream (streams/fetch-formatted-streams backtest-config)))
     (def open-stream-dv (dv open-stream))
     (def back-open-stream-dv (subvector open-stream-dv 0 half-stream-len))
     (def fore-open-stream-dv (subvector open-stream-dv (- half-stream-len max-shift) (+ half-stream-len max-shift)))
     (loop [~(qualified->simple 'i) 0 ~(qualified->simple 'robust-hyxs) []]
       (let [~(qualified->simple 'input-shifts) (get-rand-shifts 8 max-shift)
             ~(qualified->simple 'populated-xindy) (get-populated-xindy ~(qualified->simple 'input-shifts) 'back-open-stream-dv (- half-stream-len max-shift) jpy?)
             ~(qualified->simple 'hyxindy) (get-hyxindy ~(qualified->simple 'populated-xindy) (subvector back-open-stream-dv max-shift (- (dim back-open-stream-dv) max-shift)))
             ~(qualified->simple 'best-hyx) (loop [~(qualified->simple 'j) 0 ~(qualified->simple 'hyx) ~(qualified->simple 'hyxindy)]
                                              (if (>= ~(qualified->simple 'j) 15) ~(qualified->simple 'hyx)
                                                  (recur (inc ~(qualified->simple 'j))
                                                         (improve-hyxindy ~(qualified->simple 'hyx) back-open-stream-dv 'back-open-stream-dv max-shift jpy?))))
             ~(qualified->simple 'fore-hyx) (get-fore-hyx ~(qualified->simple 'best-hyx) fore-open-stream-dv 'fore-open-stream-dv max-shift jpy?)
             ~(qualified->simple 'robustness) (stats/z-score (seq (:rivulet ~(qualified->simple 'best-hyx))) (seq (:rivulet ~(qualified->simple 'fore-hyx))))
             ~(qualified->simple 'foo) (when (env/get-env-data :GA_LOGGING?) (println ~(qualified->simple 'i) ~(qualified->simple 'robustness)))]
         (if (>= ~(qualified->simple 'i) 2000) ~(qualified->simple 'robust-hyxs)
             (recur (inc ~(qualified->simple 'i))
                    (if (and (> ~(qualified->simple 'robustness) 0) 
                             (> (:score ~(qualified->simple 'best-hyx)) 0) 
                             (> (:score ~(qualified->simple 'fore-hyx)) 0))
                      (conj ~(qualified->simple 'robust-hyxs)
                            (combine-back-fore-hyxs ~(qualified->simple 'best-hyx)
                                                    ~(qualified->simple 'fore-hyx)
                                                    ~instrument))
                      ~(qualified->simple 'robust-hyxs))))))))


(comment

  (do
    (def hyxs (eval (big-thing "USD_JPY" "H1")))

    (println (count hyxs))
    (stats/mean (map #(-> % :fore :sieve last) hyxs)))
  
  (doseq [instrument ["EUR_USD" "USD_JPY" "AUD_USD"]]
    (do
      (println instrument "...")
      (let [hyxs (big-thing instrument "H1")]
        (println hyxs)
        )))
  
  (doseq [instrument ["EUR_USD" "USD_JPY" "AUD_USD"]]
    (do
      (println instrument "...")
      (let [hyxs (eval (big-thing instrument "H1"))]
        (println (count hyxs))
        (println (stats/mean (map #(-> % :fore :sieve last) hyxs)))
        (arena/post-hyxs hyxs))))

  (plot/plot-streams [(vec (concat (:beck (:back (first hyxs))) (:beck (:fore (first hyxs)))))])
  (plot/plot-streams (mapv
                      (fn [ind] (vec (concat (reductions + (vec (seq (:rivulet (:back (nth hyxs ind))))))
                                             (reductions + (vec (seq (:rivulet (:fore (nth hyxs ind)))))))))
                      (range (count hyxs))))

  )
  


(comment
  
  ;; "Fully Async Multi-currency scheduled runner"
  ;; (let [gran "M5"
  ;;       schedule-chan (async/chan)
  ;;       future-times (util/get-future-unix-times-sec gran)]

  ;;   (util/put-future-times schedule-chan future-times)

  ;;   (async/go-loop []
  ;;     (when-some [val (async/<! schedule-chan)]
  ;;       (doseq [instrument ["EUR_USD" "USD_JPY" "EUR_GBP" "AUD_USD" "EUR_JPY" "GBP_USD"
  ;;                           "USD_CHF" "AUD_JPY" "USD_CAD" "ZAR_JPY" "CHF_JPY" "EUR_CHF"
  ;;                           "NZD_USD" "EUR_CAD" "NZD_JPY" "AUD_CHF" "CAD_JPY" "CAD_CHF"]]
  ;;       ;; (doseq [instrument ["AUD_USD" "EUR_USD" "EUR_AUD"]]
  ;;         (async/go
  ;;           (let [hyxs (eval (big-thing instrument gran))
  ;;                 postable-hyxs (if (> (count hyxs) 0) hyxs [{:instrument instrument :fore {:sieve [0]}}])]
  ;;             (arena/post-hyxs postable-hyxs)))))
  ;;     (when (not (env/get-env-data :KILL_GO_BLOCKS?)) (recur))))

  ;; (doseq [instrument ["EUR_USD" "USD_JPY" "EUR_GBP" "AUD_USD" "EUR_JPY" "GBP_USD"
  ;;                     "USD_CHF" "AUD_JPY" "USD_CAD" "ZAR_JPY" "CHF_JPY" "EUR_CHF"
  ;;                     "NZD_USD" "EUR_CAD" "NZD_JPY" "AUD_CHF" "CAD_JPY" "CAD_CHF"]]
  ;;   (async/go
  ;;     (let [hyxs (eval (big-thing instrument "H1"))
  ;;           postable-hyxs (if (> (count hyxs) 0) hyxs [{:instrument instrument :fore {:sieve [0]}}])]
  ;;       ;; (arena/post-hyxs postable-hyxs)
  ;;       (let [instrument (:instrument (first postable-hyxs))
  ;;             ;; foo (println instrument)
  ;;             account-balance (oa/get-account-balance)
  ;;             target-pos (int (* account-balance (stats/mean (mapv #(-> % :fore :sieve seq vec last) postable-hyxs))))
  ;;             current-pos-data (-> (oa/get-open-positions) :positions (util/find-in :instrument instrument))
  ;;             long-pos (when current-pos-data (-> current-pos-data :long :units Integer/parseInt))
  ;;             short-pos (when current-pos-data (-> current-pos-data :short :units Integer/parseInt))
  ;;             current-pos (when current-pos-data (+ long-pos short-pos))
  ;;             units (if current-pos-data (- target-pos current-pos) target-pos)]
  ;;         (if (not= units 0)
  ;;           (do 
  ;;             (oa/send-order-request (ot/make-order-options-util instrument units "MARKET"))
  ;;               ;; (println instrument ": position changed")
  ;;               ;; (println "prev-pos: "  current-pos)
  ;;               ;; (println "target-pos: " target-pos)
  ;;               (println instrument "pos-change: " units))
  ;;           (println instrument ": nothing happened")))
  ;;       )))

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


