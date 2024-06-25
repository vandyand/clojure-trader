(ns nean.compare-functions
  (:require [clojure.tools.namespace.find :as ns-find]
            [clojure.tools.namespace.file :as ns-file]
            [clojure.java.io :as io]
            [clojure.edn :as edn]
            [clojure.string :as str]
            [clojure.set :as set]))

(defn find-namespaces-in-dir [dir]
  (->> (ns-find/find-namespaces-in-dir (io/file dir))
       (map ns-name)))

(defn require-namespace [ns]
  (try
    (require ns)
    (catch Exception e
      (println "Error requiring namespace" ns ":" (.getMessage e)))))

(defn find-functions-in-namespace [ns]
  (require-namespace ns)
  (let [vars (vals (ns-interns ns))]
    (->> vars
         (filter (fn [v]
                   (let [resolved-var (var-get v)
                         is-fn (fn? resolved-var)]
                     is-fn)))
         (map #(-> % meta :name))
         set)))

(defn find-all-functions-in-dir [dir]
  (let [namespaces (find-namespaces-in-dir dir)]
    (->> namespaces
         (mapcat find-functions-in-namespace)
         set)))

(defn read-function-names [file]
  (edn/read-string (slurp file)))

(defn compare-function-sets [all-functions traced-functions]
  (set/difference all-functions traced-functions))

(defn -main []
  (let [all-functions (find-all-functions-in-dir "src")
        _ (println "All functions found:" all-functions)
        traced-functions (read-function-names "function-names.edn")
        _ (println "Traced functions:" traced-functions)
        untraced-functions (compare-function-sets all-functions traced-functions)]
    (spit "untraced-functions.edn" (pr-str untraced-functions))
    (println "Untraced functions written to untraced-functions.edn")))

;; Run the comparison
#_(-main)