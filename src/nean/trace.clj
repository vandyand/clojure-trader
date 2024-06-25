(ns nean.trace
  (:require [clojure.tools.namespace.find :as ns-find]
            [clojure.tools.namespace.file :as ns-file]
            [clojure.java.io :as io]
            [clojure.tools.trace :as trace]
            [clojure.edn :as edn]))

(def function-names (atom #{}))

(defn custom-trace-fn [f var]
  (fn [& args]
    (let [fn-name (-> var meta :name)]
      (swap! function-names conj fn-name)
      (println "Entering function:" fn-name))
    (apply f args)))

(defn trace-ns-with-custom-fn [ns]
  (doseq [var (vals (ns-interns ns))]
    (when (fn? @var)
      (alter-var-root var (fn [f] (custom-trace-fn f var))))))

(defn find-namespaces-in-dir [dir]
  (->> (ns-find/find-namespaces-in-dir (io/file dir))
       (map ns-name)))

;; Find all namespaces in the /src directory
(def namespaces-to-trace (find-namespaces-in-dir "src"))

;; Apply custom trace to all functions in the found namespaces
(doseq [ns namespaces-to-trace]
  (trace-ns-with-custom-fn ns))

(defn save-function-names []
  (spit "function-names.edn" (pr-str @function-names)))

(defn run-traced-backtest []
  (nean.arena/run-backtest-and-procure-positions)
  (save-function-names))