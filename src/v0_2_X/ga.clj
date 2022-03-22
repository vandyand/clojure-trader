(ns v0_2_X.ga
  (:require [clojure.pprint :as pp]
            [clojure.zip :as z]
            [clojure.walk :as w]
            [v0_1_X.incubator.ga :as iga]
            [v0_1_X.incubator.strategy :as strat]
            [v0_2_X.config :as config]
            [v0_2_X.hydrate :as hyd]
            [v0_2_X.strindicator :as strindy]
            [v0_2_X.plot :as plot]))


; zip function

(defn strindy-zip [strindy]
  (z/zipper
   (fn [x] (contains? x :inputs))
   (fn [x] (seq (get x :inputs)))
   (fn [node children]
     (assoc node :inputs (vec children)))
   strindy))

; get initial population with fitnesses

(defn get-hystrindies
  ([ga-config streams] (get-hystrindies ga-config streams (get-in ga-config [:pop-config :pop-size])))
  ([ga-config streams num-strindies]
     (loop [i 0 v (transient [])]
       (if (< i num-strindies)
         (recur (inc i)
                (conj! v (hyd/get-hydrated-strindy (get-in ga-config [:backtest-config :strindy-config]) streams)))
         (persistent! v)))))

(defn get-hystrindy-fitness [hystrindy]
  (let [fitness (last (first (hystrindy :return-streams)))]
    (assoc hystrindy :fitness fitness)))

(defn get-hystrindies-fitnesses [hystrindies]
  (for [hystrindy hystrindies]
    (get-hystrindy-fitness hystrindy)))

(defn get-init-pop [ga-config streams]
  (get-hystrindies-fitnesses (get-hystrindies ga-config streams)))


; get best parents

(defn sort-hystrindies [hystrindies]
  (reverse (sort-by :fitness hystrindies)))

;; (def parents-pop (get-best-hystrindies init-pop (get-in ga-config [:pop-config :num-parents])))

; make children via mutation and crossover

; change branch function(s)
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
               (some #(= % :tree) (keys (meta (form :fn)))))
          (let [mutated-tree (iga/get-mutated-tree ((meta (form :fn)) :tree))]
            (assoc form :fn (with-meta (fn [& args] (strat/solve-tree mutated-tree args)) {:name (str mutated-tree) :tree mutated-tree})))
            ; regular node
          (some #(= % :inputs) (keys form))
          (let [n (rand-int 6)]
            (cond
              (< n 3) (assoc form :fn (rand-nth strindy/strindy-funcs))
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
          (some #(= % :fn) (keys form))
          (assoc form :fn (with-meta (constantly (rand)) {:name "rand const"}))
          :else form)
        form)) strindy)))

(defn get-mutated-strindy-repeatedly
  ([strindy strindy-config num-repeats] (get-mutated-strindy-repeatedly strindy strindy-config num-repeats 0))
  ([strindy strindy-config num-repeats repeat-num]
   (strindy/print-strindy strindy)
   (let [new-strindy (get-mutated-strindy strindy strindy-config)]
     (if (>= repeat-num num-repeats)
       new-strindy
       (get-mutated-strindy-repeatedly new-strindy strindy-config num-repeats (inc repeat-num))))))

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
  [parent-strindies config]
  (let [n (rand)
        c-pct (get-in config [:pop-config :crossover-pct])
        m-pct (get-in config [:pop-config :mutation-pct])
        strindy-config (get-in config [:backtest-config :strindy-config])]
    parent-strindies
    (cond
      (< n c-pct)
      (get-crossover-strindy parent-strindies)
      (< n (+ c-pct m-pct))
      (get-mutated-strindy-recur (rand-nth parent-strindies) strindy-config)
      :else (strindy/make-strindy strindy-config))))

(defn get-children-strindies [parent-strindies ga-config]
  (loop [v (transient [])]
    (if (< (count v) (get-in ga-config [:pop-config :num-children]))
      (recur (conj! v (get-child-strindy parent-strindies ga-config)))
      (persistent! v))))


(defn run-epoch
  ([streams ga-config] (run-epoch (sort-hystrindies (get-init-pop ga-config streams)) streams ga-config))
  ([population streams ga-config]
   (let [parents-pop (take (get-in ga-config [:pop-config :num-parents]) population)
         parents-strindies (map :strindy parents-pop)
         children-strindies (get-children-strindies parents-strindies ga-config)
         children-hystrindies (get-hystrindies-fitnesses (hyd/hydrate-strindies children-strindies streams))]
     (sort-hystrindies (into parents-pop children-hystrindies)))))

(defn run-epochs
  ([streams ga-config] (run-epochs (get-init-pop ga-config streams) streams ga-config))
  ([population streams ga-config]
   (loop [i 0 pop population]
     (let [next-gen (run-epoch pop streams ga-config)
           best-score (apply max (map :fitness next-gen))
           average (let [fitnesses (map :fitness next-gen)]
                     (/ (reduce + fitnesses) (count fitnesses)))]
       (println "gen  " i " best score: " best-score
                " avg pop score: " average)
       (if (< i (get ga-config :num-epochs)) (recur (inc i) next-gen) next-gen)))))

(def backtest-config (config/get-backtest-config-util
                      ["EUR_USD" "both" "AUD_USD" "inception" "GBP_USD" "inception" "USD_JPY" "inception"]
                      "binary" 2 6 10 1200 "H1"))

(def ga-config (config/get-ga-config 20 backtest-config (config/get-pop-config 40 0.2 0.4 0.6)))

(def streams (hyd/get-backtest-streams (get ga-config :backtest-config)))

(def best-pop (run-epochs streams ga-config))

;; (map #(strindy/print-strindy (get % :strindy)) best-pop)

;; (plot/plot-strindies (take 2 best-pop))
(plot/plot-strindies-with-intentions (take 5 best-pop) (streams :intention-streams))

(comment
  (do

    (defn combine-strindies [strindy1 strindy2]
      (-> strindy1 strindy-zip z/down (z/replace (-> strindy2 strindy-zip z/down z/node)) z/root))

    (defn rand-child [strindy]
      (-> strindy strindy-zip z/children rand-nth))

    (defn get-crossover-strindyy [strindies]
      (let [rand-strindies (shuffle strindies)
            strindy1 (first rand-strindies)
            strindy2 (last rand-strindies)
            n (rand-int 1)]
        (cond
          (= n 0) (combine-strindies strindy1 strindy2)
          (= n 1) (combine-strindies (rand-child strindy1) strindy2)
          (= n 2) (combine-strindies (rand-child strindy2) strindy1)
          (= n 3) (combine-strindies (rand-child strindy1) (rand-child strindy2)))))

    (def strindy1 (strindy/make-strindy (get backtest-config :strindy-config)))
    (def strindy2 (strindy/make-strindy (get backtest-config :strindy-config)))

    (def cstrindy (get-crossover-strindyy [strindy1 strindy2]))

    (strindy/print-strindy strindy1)
    (strindy/print-strindy strindy2)
    (strindy/print-strindy cstrindy))
  )






