(ns v0_2_X.config)

(def default-stream-config
  {:name "default"
   :id 0
   :inception true
   :intention false})

;; :incint is a string of "inception" | "intention" | "both"
(defn get-streams-config [& args]
  (reduce (fn [acc args] (conj acc {:name (first args) :incint (last args) :id (count acc)}))
          [{:name "default" :incint "inception" :id 0}] (partition 2 args)))

(defn get-stream-ids [streams-config incint]
  (reduce
   (fn [acc arg]
     (if (or (= (get arg :incint) incint)
             (= (get arg :incint) "both"))
       (conj acc (get arg :id)) acc))
   []
   streams-config)) ; Need stream ids for strindy tree creation (not tree config)

(defn get-strindy-config [tree-config streams-config]
  (let [inception-ids (get-stream-ids streams-config "inception")
        intention-ids (get-stream-ids streams-config "intention")]
    (into tree-config {:inception-ids inception-ids :intention-ids intention-ids})))

(defn get-backtest-config [num-data-points granularity streams-config strindy-config]
  {:num-data-points num-data-points
   :granularity granularity
   :streams-config streams-config
   :strindy-config strindy-config})

; Strindy tree shape config:
(defn get-tree-config 
  "return-type is string of 'binary' | 'continuous'"
  [return-type min-depth max-depth max-children]
  {:return-type return-type :min-depth min-depth :max-depth max-depth :max-children max-children})

(defn get-config [streams-vec tree-return-type tree-min-depth tree-max-depth tree-max-children
              num-data-points granularity]
  (let [streams-config (apply get-streams-config streams-vec)
        tree-config (get-tree-config tree-return-type tree-min-depth tree-max-depth tree-max-children)
        strindy-config (get-strindy-config tree-config streams-config)]
    (get-backtest-config num-data-points granularity streams-config strindy-config)))

(def config (get-config ["EUR_USD" "both" "AUD_USD" "both"] "binary" 2 6 10 1000 "H1"))



; Arena strindy: package of - backtested strindy, arena-performance {returns, z-score, other-score?}
; Live practice strindy: arena strindy + live-practive-performance {returns, z-score, other-score?}
;; (skip one of arena strindy, live practice strindy? or combine them rather?)
; Live trading strindy: live practice strindy + live-trading-performance {returns, z-score, other-score?}
