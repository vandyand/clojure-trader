(ns v0_2_X.nean_strindy
  (:require
   [uncomplicate.neanderthal.core :refer :all]
   [uncomplicate.neanderthal.native :refer :all]
   [uncomplicate.fluokitten.core :refer [fmap fmap! fold foldmap]]
   [criterium.core :refer [quick-bench with-progress-reporting]]
   [config :as config]
   [util :as util]
   [v0_2_X.streams :as streams]
   [v0_2_X.plot :as plot]))

(defn br []
  (util/bounded-rand 1 -1))

(def nean-grt (fn [x y] (->> (- x y) (* -1E10) Math/exp (+ 1) (/ 1))))

(defmacro make-hindy [& is]
  `(fmap nean-grt (xpy ~(rand-nth is) ~(rand-nth is)) (xpy  ~(rand-nth is)  ~(rand-nth is))))

(defn shift-vec [shift max-shift _vec] 
  (println shift max-shift)
  (subvec _vec  (- max-shift shift) (- (count _vec) shift)))

(defn nean-streams [streams how-many-streams?] 
  (->> 
   #(->> streams :inception-streams first (mapv :o) (shift-vec (rand-int 10) 10)) 
   repeatedly 
   (take how-many-streams?)))

(defmacro make-hindy2 [streams]
  (let [is (nean-streams streams 10)]
    is
    ;; `(fmap nean-grt (xpy ~(rand-nth is) ~(rand-nth is)) (xpy ~(rand-nth is)  ~(rand-nth is)))
    ))




(defn get-sieve-stream [strindy inception-streams]
  nil)

(defn sieve->return [sieve intention-stream]
  nil)


(comment
  (def backtest-config (config/get-backtest-config-util
                        ["EUR_USD" "both"]
                        "ternary" 1 2 3 100 "H4"))

  (def streams (streams/fetch-formatted-streams backtest-config))
  
  (make-hindy2 streams)
  
  (macroexpand '(hindy streams))
  
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
   (dv (formatted-streams->stream streams :c)))

  )


