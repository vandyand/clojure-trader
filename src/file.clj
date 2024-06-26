(ns file
  (:require
   [clojure.edn :as edn]
   [util :as util]
   [clojure.core.async :as async]
   [clojure.java.io :as io]
   [env :as env]))

(def data-folder "data/")
(def hyst-folder "hysts/")
(def lab-folder "lab/")

(defn read-file
  ([file-name]
   (edn/read-string (slurp file-name))))

(defn read-collection-file
  ([file-name] (read-collection-file file-name #"\n"))
  ([file-name newline-regex]
   (edn/read-string (clojure.string/replace (str "[" (slurp file-name) "]") newline-regex " "))))

(defn read-data-file
  ([file-name] (read-data-file file-name #"\n"))
  ([file-name newline-regex]
   (read-collection-file (str data-folder file-name) newline-regex)))

(defn write-file
  ([file-name contents] (write-file file-name contents false))
  ([file-name contents append?]
   (spit file-name (prn-str contents) :append append?)))

(defn clear-file [file-name]
  (spit (str data-folder file-name) ""))

(defn delete-file [file-name]
  (clojure.java.io/delete-file (str data-folder file-name)))

(defn delete-by-id [file-name id]
  (let [contents (read-data-file file-name)
        new-contents (filter #(not= (:id %) id) contents)]
    (clear-file file-name)
    (for [new-content new-contents]
      (write-file file-name new-content))))

(defn get-by-id [file-name id]
  (util/find-in (read-data-file file-name) :id id))

(defn open-file-writer-async [from-chan full-file-name watcher-atom]
  (async/go
    (loop []
      (when (not (env/get-env-data :KILL_GO_BLOCKS?))
        (when-some [v (async/<! from-chan)]
          (with-open [wrtr (io/writer full-file-name :append true)]
            (.write wrtr (str v "\n"))
            (when watcher-atom (swap! watcher-atom inc))))
        (recur)))))