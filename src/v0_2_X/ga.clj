(ns v0_2_X.ga
  (:require [clojure.pprint :as pp]
            [clojure.zip :as z]
            [clojure.walk :as w]
            [v0_1_X.ga :as iga]
            [v0_1_X.strategy :as strat]
            [config :as config]
            [v0_2_X.hydrate :as hyd]
            [v0_2_X.strindicator :as strindy]
            [v0_2_X.plot :as plot]
            [v0_2_X.streams :as streams]
            [env :as env]))

(defn strindy-zip [strindy]
  (z/zipper
   (fn [x] (contains? x :inputs))
   (fn [x] (seq (get x :inputs)))
   (fn [node children]
     (assoc node :inputs (vec children)))
   strindy))

(defn sort-hystrindies [hystrindies]
  (reverse (sort-by :fitness hystrindies)))

(defn get-mutated-strindy
  ([strindy strindy-config] (get-mutated-strindy strindy strindy-config 100))
  ([strindy strindy-config max-num-mutations]
   (def a (atom 0))
   (w/postwalk
    (fn [form]
      (if (and (map? form)
               (< (rand) 0.25)
               (< @a max-num-mutations))
        (cond
            ; strat tree node
          (and (some #(= % :inputs) (keys form))
               (some #(= % :tree) (keys (form :policy))))
          (let [mutated-tree (iga/get-mutated-tree (get-in form [:policy :tree]))]
            (assoc form :policy {:fn (fn [& args] (strat/solve-tree mutated-tree args)) :type "strategy" :tree mutated-tree}))
            ; regular node
          (some #(= % :inputs) (keys form))
          (let [n (rand-int 6)]
            (cond
              (< n 3) (assoc form :policy (rand-nth strindy/strindy-funcs))
              (< n 4) (strindy/make-strindy
                       (config/get-strindy-config
                        "continuous" 1 2 3
                        (get strindy-config :inception-ids)
                        (get strindy-config :intention-ids)))
              (< n 5) (if (> (count (form :inputs)) 2)
                        (let [inputs (get form :inputs)]
                          (assoc form :inputs (subvec (shuffle inputs) 0 (dec (count inputs)))))
                        form)
              (< n 6) (assoc form :inputs (into (form :inputs) [(strindy/make-input (get strindy-config :inception-ids))]))))
            ; input node
          (some #(= % :id) (keys form))
          (if (> 0.5 (rand))
            (assoc form :id (rand-nth (get strindy-config :inception-ids)))
            (assoc form :shift (first (random-sample 0.5 (range)))))
            ; rand const node
          (some #(= % :policy) (keys form))
          (assoc form :policy (let [r (rand)] {:type "rand" :value r :fn (constantly r)}))
          :else form)
        form)) strindy)))

(defn get-mutated-strindy-recur [strindy strindy-config]
  (let [mutated-strindy (get-mutated-strindy strindy strindy-config)]
    (if (= mutated-strindy strindy) (get-mutated-strindy-recur strindy strindy-config) 
        (strindy/ameliorate-strindy-recur mutated-strindy))))

(defn combine-strindies [strindy1 strindy2]
  (-> strindy1 strindy-zip z/down (z/replace (-> strindy2 strindy-zip z/down z/node)) z/root))

(defn rand-child [strindy]
  (-> strindy strindy-zip z/children rand-nth))

(defn get-crossover-strindy [strindies]
  (let [rand-strindies (shuffle strindies)
        strindy1 (first rand-strindies)
        strindy2 (last rand-strindies)
        n (rand-int 1)]
    (cond
      (= n 0) (combine-strindies strindy1 strindy2)
      (= n 1) (combine-strindies (rand-child strindy1) strindy2)
      (= n 2) (combine-strindies (rand-child strindy2) strindy1)
      (= n 3) (combine-strindies (rand-child strindy1) (rand-child strindy2)))))

(defn get-child-strindy
  [parent-strindies ga-config]
  (let [n (rand)
        c-pct (get-in ga-config [:pop-config :crossover-pct])
        m-pct (get-in ga-config [:pop-config :mutation-pct])
        strindy-config (get-in ga-config [:backtest-config :strindy-config])]
    parent-strindies
    (cond
      (< n c-pct)
      (get-crossover-strindy parent-strindies)
      (< n (+ c-pct m-pct))
      (get-mutated-strindy-recur (first (random-sample 0.1 (cycle parent-strindies))) strindy-config)
      :else (strindy/make-strindy strindy-config))))

(defn get-unique-children-hystrindies
  [parents-pop ga-config streams]
   (loop [v []]
     (if (< (count v) (get-in ga-config [:pop-config :num-children]))
       (recur
        (let [new-strindy (get-child-strindy (map :strindy parents-pop) ga-config)
              new-hystrindy (hyd/hydrate-strindy new-strindy (get ga-config :backtest-config))
              new-sieve (get new-hystrindy :sieve-stream)
              prior-sieves (map :sieve-stream (into parents-pop v))]
          (if (hyd/is-sieve-unique? new-sieve prior-sieves) (conj v new-hystrindy) v)))
       (hyd/get-hystrindies-fitnesses v))))

(defn run-epoch
  ([streams ga-config] (run-epoch (sort-hystrindies (hyd/get-init-pop ga-config)) streams ga-config))
  ([population streams ga-config]
   (let [parents-pop (take (get-in ga-config [:pop-config :num-parents]) population)
         children-pop (get-unique-children-hystrindies parents-pop ga-config streams)]
     (sort-hystrindies (into parents-pop children-pop)))))

(defn run-epochs
  ([streams ga-config] (run-epochs (sort-hystrindies (hyd/get-init-pop ga-config))streams ga-config))
  ([population streams ga-config]
   (loop [i 0 pop population]
     (let [next-gen (run-epoch pop streams ga-config)
           best-score (apply max (map :fitness next-gen))
           average (let [fitnesses (take (get-in ga-config [:pop-config :num-parents]) (map :fitness next-gen))]
                     (/ (reduce + fitnesses) (count fitnesses)))]
       (when (env/get-env-data :GA_LOGGING?) (println "gen  " i " best score: " best-score
                " avg parent score: " average))
       (when (env/get-env-data :GA_PLOTTING?) (plot/plot-with-intentions (take 5 next-gen) (streams :intention-streams)))
       (if (< i (get ga-config :num-epochs)) (recur (inc i) next-gen) next-gen)))))

(comment
  (def backtest-config (config/get-backtest-config-util
                      ;; ["EUR_USD" "both" "AUD_USD" "inception" "GBP_USD" "inception" "USD_JPY" "inception"]
                        ["EUR_USD" "intention"]
                        "long-only" 1 2 3 100 "M1"))

  (def ga-config (config/get-ga-config 10 backtest-config (config/get-pop-config 20 0.4 0.1 0.2)))

  (def streams (streams/fetch-formatted-streams (get ga-config :backtest-config)))

;; (def init-pop (hyd/get-init-pop ga-config))
  
  (def best-pop (run-epochs streams ga-config))
  )
