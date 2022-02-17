(ns arena.mock-strategy
  (:require [incubator.ga :as ga]
            [incubator.strategy :as strat]))

(def ga-config
  (let [num-epochs 20
        input-config (strat/get-input-config 10 1 100 10 10 0.1 100)
        tree-config (strat/get-tree-config
                     3 6 (strat/get-index-pairs
                          (get input-config :num-inception-streams)))
        pop-config (ga/get-pop-config 50 0.5 0.4 0.5)]
    (ga/get-ga-config num-epochs input-config tree-config pop-config)))

(def best-strat (first (ga/run-epochs ga-config)))

(def packaged-strategy best-strat)
