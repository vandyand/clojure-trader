(ns file
  (:require
   [clojure.edn :as edn]
   [v0_1_X.strategy :as strat]
   [v0_2_X.strindicator :as strindy]
   [util]))

(def data-folder "data/")
(def hyst-folder "hysts/")

(defn format-strindy-for-edn [strindy]
  (clojure.walk/postwalk
   (fn [form]
     (if (and (map? form) (some #(= % :policy) (keys form)))
       (update-in form [:policy] dissoc :fn)
       form))
   strindy))

(defn read-file [file-name]
  (edn/read-string (clojure.string/replace (str "[" (slurp (str data-folder file-name)) "]") #"\n" "")))

(defn write-file 
  ([file-name contents] (write-file file-name contents false))
  ([file-name contents append?]
  (spit file-name (prn-str contents) :append append?)))

(defn clear-file [file-name]
  (spit (str data-folder file-name) ""))

(defn delete-file [file-name]
  (clojure.java.io/delete-file (str data-folder file-name)))

(defn delete-by-id [file-name id]
  (let [contents (read-file file-name)
        new-contents (filter #(not= (:id %) id) contents)]
    (clear-file file-name)
    (for [new-content new-contents]
      (write-file file-name new-content))))

(defn get-by-id [file-name id]
  (util/find-in (read-file file-name) :id id))

(defn hyst->file-name [hyst]
  (str (clojure.string/join
        "-"
        (conj
         (rest
          (map
           (fn [stream-conf] (if (= "inception" (get stream-conf :incint))
                               (clojure.string/lower-case (get stream-conf :name))
                               (str "Target_" (get stream-conf :name))))
           (-> hyst :backtest-config :streams-config)))
         (-> hyst :backtest-config :num-data-points)
         (-> hyst :backtest-config :granularity)))
       ".edn"))

(defn save-hystrindy-to-file
  [hystrindy]
   (let [formatted-hystrindy 
         (assoc 
          hystrindy 
          :strindy 
          (format-strindy-for-edn 
           (get hystrindy 
            :strindy)))
         file-name (hyst->file-name hystrindy)]
     (write-file (str data-folder hyst-folder file-name) formatted-hystrindy true)))

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
   (let [formatted-hystrindies (read-file (str hyst-folder file-name))]
     (for [formatted-hystrindy formatted-hystrindies]
       (deformat-hystrindy formatted-hystrindy)))))
