(ns find-filenames
  (:require [clojure.java.io :as io]
            [clojure.string :as str]
            [clojure.edn :as edn]
            [clojure.java.shell :as shell]
            [clojure.set :as set]
            [clojure.tools.logging :as log]))

(defn read-function-names [filename]
  (with-open [r (io/reader filename)]
    (edn/read (java.io.PushbackReader. r))))

(defn normalize-path [path]
  (-> path
      (str/replace #"//+" "/")
      (str/replace "\\" "/")))

(defn find-filename-for-function [function-name]
  (let [command (str "grep -rl \"defn " function-name "\" src/")]
    (->> (shell/sh "bash" "-c" command)
         :out
         str/trim
         str/split-lines
         (map normalize-path)
         (filter #(not (str/blank? %)))
         set)))

(defn find-filenames [function-names]
  (reduce (fn [acc fn-name]
            (let [filenames (find-filename-for-function fn-name)]
              (set/union acc filenames)))
          #{}
          function-names))

(defn write-set-to-edn [data output-file]
  (with-open [w (io/writer output-file)]
    (binding [*out* w]
      (prn data))))

(defn list-all-files [dir]
  (->> (file-seq (io/file dir))
       (filter #(.isFile %))
       (map #(.getPath %))
       (map normalize-path)
       (filter #(str/starts-with? % "src/"))
       set))

(defn -main []
  (let [function-names (read-function-names "function-names.edn")
        found-filenames (find-filenames function-names)
        all-filenames (list-all-files "src")
        missing-filenames (set/difference all-filenames found-filenames)]

    ;; Logging the data being compared
    (log/info "Found filenames:" found-filenames)
    (log/info "All filenames:" all-filenames)
    (log/info "Missing filenames:" missing-filenames)

    (write-set-to-edn found-filenames "found-filenames.edn")
    (write-set-to-edn missing-filenames "missing-filenames.edn")
    (println "Found filenames written to found-filenames.edn")
    (println "Missing filenames written to missing-filenames.edn")))

;; Uncomment the following line to run the script directly
(-main)