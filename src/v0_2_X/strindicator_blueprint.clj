(ns v0-2-X.strindicator-config
  (:require [v0_2_X.strindicator :as strindy]
            [v0_1_X.incubator.strategy :as strat]
            [v0_1_X.incubator.inputs :as inputs]))


(def strindy-blueprint 
  {:return {:type "binary"
            :range nil}
   :num-data-points 1000
   :incenpion [{:type "instrument"
                :name "EUR_USD"}
               {:type "integers"
                :name "integers"}]
   :intention [{:type "instrument"
                :name "EUR_USD"}]
   :body {:min-depth 8 :max-depth 10 :max-num-children 10}})