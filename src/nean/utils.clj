(ns nean.utils
  (:require [clojure.java.io :as io]
            [clojure.edn :as edn]))

(defn write-file [filename content]
  (with-open [w (io/writer filename)]
    (binding [*out* w]
      (prn content))))

(defn read-file [filename]
  (with-open [r (io/reader filename)]
    (edn/read r)))