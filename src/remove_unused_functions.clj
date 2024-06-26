(ns remove-unused-functions
  (:require [clojure.java.io :as io]
            [clojure.edn :as edn]
            [clojure.string :as str]))

(defn read-unused-functions [file]
  (edn/read-string (slurp file)))

(defn find-clojure-files [dir]
  (->> (file-seq (io/file dir))
       (filter #(and (.isFile %)
                     (str/ends-with? (.getName %) ".clj")))))

(defn remove-unused-functions-from-file [file unused-functions]
  (let [content (slurp file)
        pattern (re-pattern (str "(?s)\\(defn\\s+(" (str/join "|" unused-functions) ")\\b.*?\\)"))
        updated-content (str/replace content pattern "")]
    (spit file updated-content)))

(defn -main []
  (let [unused-functions (read-unused-functions "untraced-functions.edn")
        clojure-files (find-clojure-files "src")]
    (doseq [file clojure-files]
      (remove-unused-functions-from-file file unused-functions))
    (println "Unused functions removed.")))

;; Run the script
(-main)