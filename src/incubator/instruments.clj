(ns instruments
  (:require [clojure.data.csv :as csv]
            [clojure.java.io :as io]
            [strategy :as strat]
            [vec_strategy :as vat]
            [ga :as ga]))


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
   (def input-config (strat/get-inputs-config 20 (count eurusd) 0.05 1 0 100))
   (def tree-config (strat/get-tree-config 2 6 (vat/get-index-pairs (input-config :num-input-streams))))
   (def input-streams (strat/get-input-streams input-config))
   (def eurusd-delta (strat/get-stream-delta eurusd "eurusd delta"))
   (def input-and-eurusd-streams {:input-streams input-streams :target-stream eurusd :target-stream-delta eurusd-delta})
   (def ga-config (ga/get-ga-config 50 0.2 0.1 0.9 input-and-eurusd-streams input-config tree-config))
   (def init-pop (ga/get-init-pop ga-config))
   (def best-strats (ga/run-epochs 50 init-pop ga-config))))
