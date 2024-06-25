(ns compile-master
  (:require [clojure.java.io :as io]
            [clojure.string :as str]))

(defn get-all-files [dir]
  (filter #(.isFile %) (file-seq (io/file dir))))

(defn read-file [file]
  (slurp file))

(defn remove-namespaces [content]
  (-> content
      (str/replace #"\(ns\s+[^\)]+\)" "")
      (str/replace #"\b\w+/\b" "")))

(defn compile-master-base-file [src-dir output-file]
  (let [files (get-all-files src-dir)
        master-base-content (apply str (map #(remove-namespaces (read-file %)) files))]
    (spit output-file master-base-content)))

;; Usage
#_(compile-master-base-file "src" "master_base.clj")