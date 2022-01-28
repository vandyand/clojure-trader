(ns instruments
  (:require [clojure.data.csv :as csv]
            [clojure.java.io :as io]
            [strategy :as strat]
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

(def eurusd (with-meta (subvec (format-csv-data (get-csv-data "eurusd.csv")) 0 543) {:name "eurusd"}))

(strat/plot-stream eurusd)

(def input-config (strat/get-input-config 543 0.01 0.01 0 100))
(def input-streams (strat/get-input-streams 4 input-config))

(def eurusd-delta (strat/get-stream-delta eurusd "eurusd delta"))

(def input-and-eurusd-streams {:input-streams input-streams :target-stream eurusd :target-stream-delta eurusd-delta})


(def ga-config (ga/get-ga-config 543 50 0.4 0.3 0.5 input-and-eurusd-streams))
(def init-pop (ga/get-init-pop ga-config))

(def best-strats (ga/run-epochs 20 init-pop ga-config))
