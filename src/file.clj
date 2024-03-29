(ns file
  (:require
   [clojure.edn :as edn]
   [v0_1_X.strategy :as strat]
   [v0_2_X.strindicator :as strindy]
   [util :as util]
   [clojure.core.async :as async]
   [clojure.java.io :as io]
   [env :as env]))

(def data-folder "data/")
(def hyst-folder "hysts/")
(def lab-folder "lab/")

(defn format-strindy-for-edn [strindy]
  (clojure.walk/postwalk
   (fn [form]
     (if (and (map? form) (some #(= % :policy) (keys form)))
       (update-in form [:policy] dissoc :fn)
       form))
   strindy))

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

(defn format-hyst-for-edn [hyst]
  (assoc hyst :strindy (format-strindy-for-edn (get hyst :strindy))))

(defn save-hystrindy-to-file
  ([hyst] (save-hystrindy-to-file hyst hyst-folder))
  ([hystrindy folder]
   (let [formatted-hystrindy (format-hyst-for-edn hystrindy)
         file-name (util/config->file-name hystrindy)]
     (write-file (str data-folder folder file-name) formatted-hystrindy true))))

(defn save-hystrindies-to-file
  ([hystrindies]
   (for [hyst hystrindies]
     (save-hystrindy-to-file hyst))))

(defn deformat-hystrindy [formatted-hystrindy]
  (clojure.walk/postwalk
   (fn [form]
     (if (and (map? form) (some #(= % :policy) (keys form)))
       (let [form-type (get-in form [:policy :type])
             func (cond (= form-type "rand")
                        (constantly (get-in form [:policy :value]))
                        (some #(= % :tree) (keys (form :policy)))
                        (fn [& args] (strat/solve-tree (get-in form [:policy :tree]) args))
                        :else (:fn (util/find-in strindy/strindy-funcs :type form-type)))]
         (assoc form :policy (into (:policy form) {:fn func})))
       form))
   formatted-hystrindy))

(defn get-hystrindies-from-file
  ([] (get-hystrindies-from-file "hystrindies.edn"))
  ([file-name]
   (let [formatted-hystrindies (read-data-file (str hyst-folder file-name))]
     (for [formatted-hystrindy formatted-hystrindies]
       (deformat-hystrindy formatted-hystrindy)))))

(defn open-file-writer-async [from-chan full-file-name watcher-atom]
  (async/go
    (loop []
      (when (not (env/get-env-data :KILL_GO_BLOCKS?))
        (when-some [v (async/<! from-chan)]
          (with-open [wrtr (io/writer full-file-name :append true)]
            (.write wrtr (str v "\n"))
            (when watcher-atom (swap! watcher-atom inc))))
        (recur)))))