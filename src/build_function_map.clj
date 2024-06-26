(ns build-function-map
  (:require
   [clojure.edn :as edn]
   [clojure.java.io :as io]
   [clojure.string :as str]
   [clojure.set :as set]
   [clojure.java.shell :as shell]))

(defn read-function-names [file]
  (edn/read-string (slurp file)))

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

(defn find-functions-in-dir [dir function-names]
  (reduce (fn [acc fn-name]
            (let [filenames (find-filename-for-function fn-name)]
              (reduce (fn [acc filename]
                        (update acc filename (fnil conj #{}) fn-name))
                      acc
                      filenames)))
          {}
          function-names))

(defn -main []
  (let [function-names (read-function-names "function-names.edn")
        function-map (find-functions-in-dir "src" function-names)]
    (spit "function-map.edn" (prn-str function-map))
    (println "Function map written to function-map.edn")))

;; Call the main function to execute the script
(-main)