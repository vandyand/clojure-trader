;; (ns nean.nindy
;;   (:require [config :as config]
;;             [helpers :as hlp]
;;             [stats :as stats]
;;             [uncomplicate.fluokitten.core :refer [fmap]]
;;             [uncomplicate.neanderthal.core :refer :all]
;;             [uncomplicate.neanderthal.native :refer :all]
;;             [util :as util]
;;             [plot :as plot]
;;             [v0_2_X.streams :as streams]
;;             [v0_2_X.strindicator :as strindy]))

;; (defn br []
;;   (util/bounded-rand 1 -1))

;; (def nean-grt (fn [x y] (->> (- x y) (* -1E10) Math/exp (+ 1) (/ 1) (* -2) (+ 1))))

;; ;; (def x (dv [1 2 3]))
;; ;; (def y (dv [1 2 3]))
;; ;; (def z (dv [1 2 3]))

;; ;; (defn defns [var-names streams]
;; ;;   (map-indexed
;; ;;    (list 'def var-name stream)))

;; (defn get-axindy
;;   ([input-chars min-depth max-depth] (get-axindy 0 input-chars min-depth max-depth))
;;   ([depth input-chars min-depth max-depth]
;;    (if
;;     (or (< depth min-depth) (and (hlp/rand-bool) (<= depth (dec max-depth))))
;;      (list (br) (get-axindy (inc depth) input-chars min-depth max-depth)
;;            (br) (get-axindy (inc depth) input-chars min-depth max-depth))
;;      (-> input-chars rand-nth))))

;; (defn get-xindy
;;   ([input-chars min-depth max-depth] (get-xindy 0 input-chars min-depth max-depth))
;;   ([depth input-chars min-depth max-depth]
;;    (if
;;     (or (< depth min-depth) (and (hlp/rand-bool) (<= depth (dec max-depth))))
;;      (list (get-xindy (inc depth) input-chars min-depth max-depth)
;;            (get-xindy (inc depth) input-chars min-depth max-depth))
;;      (-> input-chars rand-nth))))

;; ;; (defn solve-axindy [form input-vec len]
;; ;;   (if (= (type form) java.lang.Long)
;; ;;     (list (subvector input-vec form len))
;; ;;     (list 'axpy (nth form 0)
;; ;;           (solve-axindy (nth form 1) input-vec len)
;; ;;           (nth form 2)
;; ;;           (solve-axindy (nth form 3) input-vec len))))


;; (defn expand-axindy [form]
;;   (if (or (= (type form) clojure.lang.Symbol) (= (type form) clojure.lang.Keyword))
;;     form
;;     (list 'axpy (nth form 0)
;;           (expand-axindy (nth form 1))
;;           (nth form 2)
;;           (expand-axindy (nth form 3)))))

;; (defn expand-xindy [form]
;;   (if (or (= (type form) clojure.lang.Symbol) (= (type form) clojure.lang.Keyword))
;;     form
;;     (list 'xpy (expand-xindy (nth form 0))
;;           (expand-xindy (nth form 1)))))

;; (defn streams->open-stream
;;   "Takes streams from streams/fetch-formatted-streams"
;;   [streams]
;;   (->> streams :inception-streams first (mapv :o)))

;; (defn qualified->simple [symb]
;;   (-> symb str (clojure.string/split #"/") last symbol))

;; (defn get-simple-axindy [weights input-chars]
;;   `(axpy ~@(interleave weights input-chars)))

;; (defn get-rand-shifts [_num max-shift]
;;   (vec (take _num (repeatedly #(rand-int max-shift)))))

;; (defn get-rand-weights [_num]
;;   (vec (take _num (repeatedly #(util/bounded-rand -1 1)))))

;; (defn get-populated-axindy [input-shifts weights stream-len]
;;   (let [num-inputs-per (int (/ (count input-shifts) 2))
;;         input-chars (util/mapv-indexed (fn [ind _] (-> ind (+ 97) char str symbol)) input-shifts)
;;         form `(let [~input-chars
;;                     [~@(map
;;                         (fn [item] `(subvector open-stream-dv ~item ~stream-len))
;;                         input-shifts)]]
;;                 (axpy 100 ~(get-simple-axindy (subvec weights 0 num-inputs-per) (subvec input-chars 0 num-inputs-per))
;;                       -100 ~(get-simple-axindy (subvec weights num-inputs-per) (subvec input-chars num-inputs-per))))]
;;     {:input-shifts input-shifts :input-weights weights :form form :sieve (-> form eval seq vec)}))

;; (defn get-performance [intention-stream sieve]
;;   (strindy/sieve->rivulet sieve (strindy/stream->delta-stream intention-stream)))

;; (defn get-hyxindy [populated-xindy intention-stream]
;;   (let [rivulet (get-performance intention-stream (get populated-xindy :sieve))]
;;     (assoc populated-xindy :rivulet rivulet :beck (vec (reductions + rivulet)) :score (stats/score-x rivulet))))

;; (defn in-range [val range-low range-high]
;;   (and (>= val range-low) (<= val range-high)))

;; (defn modify-input-shifts [input-shifts max-shift]
;;   (mapv
;;    (fn [shift]
;;      (let [new-shift (-> 41 rand-int (- 20) (+ shift))]
;;        (if (in-range new-shift 0 max-shift) new-shift shift)))
;;    input-shifts))

;; (defn modify-input-weights [input-weights]
;;   (mapv
;;    (fn [weight]
;;      (+ weight (util/bounded-rand -0.25 0.25)))
;;    input-weights))

;; (defn improve-hyaxindy [hyaxindy open-stream stream-len max-shift]
;;   (let [toggler (hlp/rand-bool)
;;         new-shifts (if toggler (:input-shifts hyaxindy) (modify-input-shifts (:input-shifts hyaxindy) max-shift))
;;         new-weights (if (not toggler) (:input-weights hyaxindy) (modify-input-weights (:input-weights hyaxindy)))
;;         new-hyaxindy (get-hyxindy (get-populated-axindy new-shifts new-weights (- stream-len max-shift)) (subvec open-stream max-shift))]
;;     (if (> (:score new-hyaxindy) (:score hyaxindy))
;;       (do
;;         (plot/plot-streams [(:beck new-hyaxindy) (plot/zero-stream (subvec open-stream max-shift))])
;;         new-hyaxindy)
;;       hyaxindy)))

;; (comment
;;   (do
;;     (def stream-len 4000)
;;     (def max-shift 100)

;;     (def backtest-config (config/get-backtest-config-util
;;                           ["EUR_USD" "both"]
;;                           "ternary" 1 2 3 stream-len "H1"))

;;     (def open-stream (streams->open-stream (streams/fetch-formatted-streams backtest-config)))

;;     (def open-stream-dv (dv open-stream))

;;     (def input-shifts (get-rand-shifts 8 max-shift))
    
;;     (def input-weights (get-rand-weights 8))

;;     (def populated-axindy (get-populated-axindy input-shifts input-weights (- stream-len max-shift)))

;;     (def hyaxindy (get-hyxindy populated-axindy (subvec open-stream max-shift)))

;;     ;; (plot/plot-streams [(:beck hyxindy) (plot/zero-stream (subvec open-stream max-shift))])
    
;;     (def best-hyax (loop [i 0 hyax hyaxindy] (if (>= i 2000) hyax (recur (inc i) (improve-hyaxindy hyax open-stream stream-len max-shift)))))
;;     )



;;   ;; comment end 
;;   )

;; (comment
;;   (def backtest-config (config/get-backtest-config-util
;;                         ["EUR_USD" "both"]
;;                         "ternary" 1 2 3 4000 "H1"))

;;   (def open-stream-dv (dv (streams->open-stream (streams/fetch-formatted-streams backtest-config))))

;;   (def aaxindy '(0.6176727490832976
;;                  a
;;                  -0.11755608865794187
;;                  (0.7371670008498643 b -0.8446439492317692 a)))

;;   (get-axindy '[a b c d] 2 3)

;;   (expand-axindy aaxindy)

;;   (let [input-shifts (vec (take 5 (repeatedly #(rand-int 50))))
;;         input-chars (util/mapv-indexed (fn [ind _] (-> ind (+ 97) char str symbol)) input-shifts)
;;         form `(let [~input-chars
;;                     [~@(map
;;                         (fn [item] `(subvector open-stream-dv ~item 150))
;;                         input-shifts)]]
;;                 ~(expand-axindy (get-axindy input-chars 3 4)))]
;;     form)

;;   (defn get-simple-xindy [input-chars]
;;     `(xpy ~@input-chars))

;;   (let [num-inputs-per 2
;;         input-shifts (vec (take (* 2 num-inputs-per) (repeatedly #(rand-int 50))))
;;         input-chars (util/mapv-indexed (fn [ind _] (-> ind (+ 97) char str symbol)) input-shifts)
;;         form `(let [~input-chars
;;                     [~@(map
;;                         (fn [item] `(subvector open-stream-dv ~item 3950))
;;                         input-shifts)]]
;;                 (fmap nean-grt
;;                       ~(get-simple-xindy (subvec input-chars 0 num-inputs-per))
;;                       ~(get-simple-xindy (subvec input-chars num-inputs-per))))]
;;     form)

;;   (let [input-shifts (vec (take 5 (repeatedly #(rand-int 50))))
;;         input-chars (util/mapv-indexed (fn [ind _] (-> ind (+ 97) char str symbol)) input-shifts)
;;         form `(let [~input-chars
;;                     [~@(map
;;                         (fn [item] `(subvector open-stream-dv ~item 150))
;;                         input-shifts)]]
;;                 ~(expand-xindy (get-xindy input-chars 3 4)))]
;;     form)

;;   `(let [~(qualified->simple ::a) (subvector open-stream-dv ~(rand-int 10) 10)
;;          ~(qualified->simple ::b) (subvector open-stream-dv ~(rand-int 10) 10)]
;;      ~(expand-axindy aaxindy))

;;   ;; (solve-axindy aaxindy open-stream-dv 10)


;;   ;; end of comment
;;   )

;; (comment

;;   (defn formatted-streams->stream
;;     "Takes formatted streams from streams/fetch-formatted-streams
;;    which is a map of keys :inception-streams and :intention-streams"
;;     [streams _key]
;;     (->> streams :inception-streams first (mapv _key)))


;;   (def backtest-config (config/get-backtest-config-util
;;                         ["EUR_USD" "both"]
;;                         "ternary" 1 2 3 100 "H4"))

;;   (def streams (streams/fetch-formatted-streams backtest-config))

;;   (def o (dv (formatted-streams->stream streams :o)))
;;   (def h (dv (formatted-streams->stream streams :h)))
;;   (def l (dv (formatted-streams->stream streams :l)))
;;   (def c (dv (formatted-streams->stream streams :c)))

;;   (let [expression (macroexpand
;;                     '(make-hindy o h l c))
;;         hydrated (-> expression eval seq)]
;;     {:expression expression :hydrated hydrated})

;;   (make-hindy
;;    (dv (formatted-streams->stream streams :o))
;;    (dv (formatted-streams->stream streams :h))
;;    (dv (formatted-streams->stream streams :l))
;;    (dv (formatted-streams->stream streams :c))))


