(ns v0_2_X.config)

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

(defn get-strindy-config 
  ([return-type min-depth max-depth max-children inception-ids intention-ids]
   {:return-type return-type
    :min-depth min-depth
    :max-depth max-depth
    :max-children max-children
    :inception-ids inception-ids
    :intention-ids intention-ids})
  ([tree-config streams-config]
  (let [inception-ids (get-stream-ids streams-config "inception")
        intention-ids (get-stream-ids streams-config "intention")]
    (into tree-config {:inception-ids inception-ids :intention-ids intention-ids}))))

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

(defn get-backtest-config-util [streams-vec tree-return-type tree-min-depth tree-max-depth tree-max-children
                                num-data-points granularity]
  (let [streams-config (apply get-streams-config streams-vec)
        tree-config (get-tree-config tree-return-type tree-min-depth tree-max-depth tree-max-children)
        strindy-config (get-strindy-config tree-config streams-config)]
    (get-backtest-config num-data-points granularity streams-config strindy-config)))


; GA config: add GA config to config... or keep it separate? That works. It makes more sense to keep it separate because
; ga and strindies are really two separate entities. Then for mature strindies, we can package them up and ship to arena.

(defn product-int [whole pct] (Math/round (double (* whole pct))))

(defn  get-pop-config [pop-size parent-pct crossover-pct mutation-pct]
  (assoc {:pop-size pop-size
          :parent-pct parent-pct
          :crossover-pct crossover-pct
          :mutation-pct mutation-pct}
         :num-parents (product-int pop-size parent-pct)
         :num-children (product-int pop-size (- 1.0 parent-pct))))

(defn get-ga-config [num-epochs backtest-config pop-config]
  {:num-epochs num-epochs
   :backtest-config backtest-config
   :pop-config pop-config})

(comment
  (def backtest-config (get-backtest-config-util ["EUR_USD" "both" "AUD_USD" "both"] "binary" 2 6 10 100 "H1"))
  
  (println (v0_2_X.strindicator/make-strindy (:strindy-config backtest-config)))
  
  
  (def ga-config (get-ga-config 5 backtest-config (get-pop-config 20 0.5 0.4 0.4)))
  )

; Arena strindy: package of - backtested populated strindy, arena-performance {returns, z-score, other-score?}
; Live practice strindy: arena strindy + live-practive-performance {returns, z-score, other-score?}
;; (skip one of arena strindy, live practice strindy? or combine them rather?)
; Live trading strindy: live practice strindy + live-trading-performance {returns, z-score, other-score?}
