(ns v0_2_X.ga
  (:require [clojure.pprint :as pp]
            [clojure.zip :as z]
            [v0_2_X.config :as config]
            [v0_2_X.hydrate :as hyd]
            [v0_2_X.strindicator :as strindy]
            [v0_2_X.oanda_strindicator :as ostrindy]))

(def backtest-config (config/get-backtest-config-util
                      ["EUR_USD" "both" "AUD_USD" "inception" "GBP_USD" "inception" "USD_JPY" "inception"]
                      "binary" 2 2 3 12 "H1"))
(def ga-config (config/get-ga-config 5 backtest-config (config/get-pop-config 20 0.5 0.4 0.4)))


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
  ([ga-config] (get-hystrindies ga-config (get-in ga-config [:pop-config :pop-size])))
  ([ga-config num-strindies]
   (let [streams (hyd/get-backtest-streams (get ga-config :backtest-config))]
     (loop [i 0 v (transient [])]
       (if (< i num-strindies)
         (recur (inc i)
                (conj! v (hyd/get-hydrated-strindy (get-in ga-config [:backtest-config :strindy-config]) streams)))
         (persistent! v))))))

(defn get-hystrindy-fitness [hystrindy]
  (let [fitness (last (first (hystrindy :return-streams)))]
    (assoc hystrindy :fitness fitness)))

(defn get-hystrindies-fitnesses [hystrindies]
  (for [hystrindy hystrindies]
    (get-hystrindy-fitness hystrindy)))

(defn get-init-pop [ga-config]
  (get-hystrindies-fitnesses (get-hystrindies  ga-config)))

(def init-pop (get-init-pop ga-config))

; get best parents

(defn get-best-hystrindies [hystrindies num]
  (take num (reverse (sort-by :fitness hystrindies))))

(def parents-pop (get-best-hystrindies init-pop (get-in ga-config [:pop-config :num-parents])))

; make children via mutation and crossover

(defn rand-bool []
  (> 0.5 (rand)))

(defn rand-child [loc]
  (if
   (z/branch? loc)
    (rand-nth (z/children loc))
    loc))

(defn prune-rand-child [loc]
  (if (z/branch? loc) (-> loc (z/replace (-> loc (rand-child) (z/node))))
      loc))

(defn new-rand-child [loc subtree-config]
  (if (z/branch? loc)
    (let [new-node (strindy/make-strindy-recur subtree-config)]
      (-> loc (rand-child) (z/replace new-node) (z/up))) loc))

(defn rand-bottom-loc
  "recursively dives a tree until it finds a bool, then returns it's 
   parent node"
  [loc] (if (not (z/branch? loc))  (z/up loc) (rand-bottom-loc
                                               (rand-child loc))))

(defn combine-node-branches [node1 node2]
  (let [znode1 (strindy-zip node1)
        znode2 (strindy-zip node2)]
   (if
   (and
    (z/branch? znode1)
    (z/branch? znode2)
    (-> znode1
        (rand-child)
        (z/replace (-> znode2 (rand-child) (z/node)))
        (z/root))
    node1)))

(def strindy (strindy/make-strindy-recur (get backtest-config :strindy-config)))

(-> strindy (strindy-zip) (z/down) (z/right) (z/children))

; combine with parents to get new population with fitnesses

; repeat
