(ns config)

;; :incint is a string of "inception" | "intention" | "both"
(defn get-streams-config [& args]
  (reduce (fn [acc args] (conj acc {:name (first args) :incint (last args) :id (count acc)}))
          [] (partition 2 args)))

(defn get-streams-info 
  ([streams-config incint] (get-streams-info streams-config incint :id))
  ([streams-config incint target-key]
  (reduce
   (fn [acc arg]
     (if (or (= (get arg :incint) incint)
             (= (get arg :incint) "both"))
       (conj acc (get arg target-key)) acc))
   []
   streams-config))) ; Need stream ids for strindy tree creation (not tree config)

(defn get-strindy-config 
  "don't worry, these overrides return the same structure!"
  ([return-type min-depth max-depth max-children inception-ids intention-ids]
   {:return-type return-type
    :min-depth min-depth
    :max-depth max-depth
    :max-children max-children
    :inception-ids inception-ids
    :intention-ids intention-ids})
  ([tree-config streams-config]
  (let [inception-ids (get-streams-info streams-config "inception")
        intention-ids (get-streams-info streams-config "intention")]
    (into tree-config {:inception-ids inception-ids :intention-ids intention-ids}))))

(defn get-backtest-config 
  ([num-data-points granularity streams-config strindy-config] (get-backtest-config num-data-points 0 granularity streams-config strindy-config))
  ([num-data-points shift-data-points granularity streams-config strindy-config] (get-backtest-config num-data-points shift-data-points granularity "balance" streams-config strindy-config))
  ([num-data-points shift-data-points granularity fitness-type streams-config strindy-config]
  {:num-data-points num-data-points
   :shift-data-points shift-data-points
   :granularity granularity
   :fitness-type fitness-type
   :streams-config streams-config
   :strindy-config strindy-config}))

; Strindy tree shape config:
(defn get-tree-config
  "return-type is string of 'long-only' | 'short-only' | 'ternary' (long and short) | 'continuous'"
  [return-type min-depth max-depth max-children]
  {:return-type return-type :min-depth min-depth :max-depth max-depth :max-children max-children})

(defn get-backtest-config-util 
  ([streams-vec tree-return-type tree-min-depth tree-max-depth tree-max-children num-data-points granularity]
   (get-backtest-config-util streams-vec tree-return-type tree-min-depth tree-max-depth tree-max-children 
                             num-data-points 0 granularity "sharpe"))
  ([streams-vec tree-return-type tree-min-depth tree-max-depth tree-max-children num-data-points granularity fitness-type]
   (get-backtest-config-util streams-vec tree-return-type tree-min-depth tree-max-depth tree-max-children 
                             num-data-points 0 granularity fitness-type))
  ([streams-vec tree-return-type tree-min-depth tree-max-depth tree-max-children
                                num-data-points shift-data-points granularity fitness-type]
  (let [streams-config (apply get-streams-config streams-vec)
        tree-config (get-tree-config tree-return-type tree-min-depth tree-max-depth tree-max-children)
        strindy-config (get-strindy-config tree-config streams-config)]
    (get-backtest-config num-data-points shift-data-points granularity fitness-type streams-config strindy-config))))

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

(defn get-factory-config [factory-num-produced ga-config]
  (assoc ga-config :factory-num-produced factory-num-produced))

(defn get-factory-config-util [backtest-config-args pop-config-args ga-num-epochs factory-num-produced]
  (let [backtest-config (apply get-backtest-config-util backtest-config-args)
        pop-config (apply get-pop-config pop-config-args)
        ga-config (get-ga-config ga-num-epochs backtest-config pop-config)]
    (get-factory-config factory-num-produced ga-config)))

(defn xindy-config [num-shifts max-shift]
  {:num-shifts num-shifts :max-shift max-shift})

(defn xindy-pop-config [pop-size parents-arg]
  (let [num-parents (if (< parents-arg 1) (int (* pop-size parents-arg)) parents-arg)
        num-children (- pop-size num-parents)]
    {:pop-size pop-size :num-parents num-parents :num-children num-children}))

(defn xindy-ga-config [num-generations stream-count back-pct]
  {:num-generations num-generations :stream-count stream-count :back-pct back-pct})


(comment
  (def backtest-config (get-backtest-config-util ["EUR_USD" "both" "AUD_USD" "both"] "long-only" 2 6 10 100 "H1"))
  
  (println (v0_2_X.strindicator/make-strindy (:strindy-config backtest-config)))
  
  
  (def ga-config (get-ga-config 5 backtest-config (get-pop-config 20 0.5 0.4 0.4)))
  )

; Arena strindy: package of - backtested populated strindy, arena-performance {returns, z-score, other-score?}
; Live practice strindy: arena strindy + live-practive-performance {returns, z-score, other-score?}
;; (skip one of arena strindy, live practice strindy? or combine them rather?)
; Live trading strindy: live practice strindy + live-trading-performance {returns, z-score, other-score?}
