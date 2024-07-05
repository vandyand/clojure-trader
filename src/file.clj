(ns file
  (:require
   [clojure.edn :as edn]
   [util :as util]
   [clojure.core.async :as async]
   [clojure.java.io :as io]
   [env :as env]
   [clojure.data.fressian :as fressian]))

(def data-folder "data/")

(defn read-uncompressed-file
  ([file-name]
   (edn/read-string (slurp file-name))))

(defn read-file
  ([file-name]
   (with-open [in (io/input-stream file-name)]
     (fressian/read in))))

(defn read-collection-file
  ([file-name] (read-collection-file file-name #"\n"))
  ([file-name newline-regex]
   (edn/read-string (clojure.string/replace (str "[" (slurp file-name) "]") newline-regex " "))))

(defn read-data-file
  ([file-name] (read-data-file file-name #"\n"))
  ([file-name newline-regex]
   (read-collection-file (str data-folder file-name) newline-regex)))

(defn write-uncompressed-file
  ([file-name contents] (write-uncompressed-file file-name contents false))
  ([file-name contents append?]
   (spit file-name (prn-str contents) :append append?)))

(defn write-file
  ([file-name contents]
   (with-open [out (io/output-stream file-name)]
     (let [writer (fressian/create-writer out)]
       (fressian/write-object writer contents)))))

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