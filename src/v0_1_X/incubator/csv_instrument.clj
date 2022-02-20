(ns v0_1_X.incubator.csv_instrument
  (:require [clojure.data.csv :as csv]
            [clojure.java.io :as io]
            [v0_1_X.incubator.strategy :as strat]
            [v0_1_X.incubator.ga :as ga]))

(defn get-csv-data [file-name]
  (with-open [reader (io/reader file-name)]
    (doall
     (csv/read-csv reader))))

(defn format-csv-data [data]
  (->> data
       (rest)
       (map last)
       (mapv #(Double/parseDouble %))))

(time
 (do
   (def eurusd (with-meta (subvec (format-csv-data (get-csv-data "eurusd.csv")) 0 543) {:name "eurusd"}))
   (def input-config (strat/get-input-config 20 (count eurusd) 0.05 1 0 100))
   (def tree-config (strat/get-tree-config 2 6 (strat/get-index-pairs (input-config :num-input-streams))))
   (def input-streams (strat/get-input-streams input-config))
   (def eurusd-delta (strat/get-stream-delta eurusd "eurusd delta"))
   (def zeroed-eurusd (with-meta (vec (for [price eurusd] (- price (first eurusd)))) {:name "zeroed eurusd"}))
   (def input-and-eurusd-streams {:input-streams input-streams :intention-stream zeroed-eurusd :intention-stream-delta eurusd-delta})
   (def pop-config (ga/get-pop-config 40 0.5 0.4 0.4))
   (def ga-config (ga/get-ga-config 20 input-config tree-config pop-config input-and-eurusd-streams))
   (def init-pop (ga/get-init-pop ga-config))
   (def best-strats (ga/run-epochs 10 init-pop ga-config))
   (ga/plot-strats-with-input-intention-streams (take 5 best-strats) input-and-eurusd-streams)
   (ga/get-strats-info (take 5 best-strats))))

