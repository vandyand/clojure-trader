(ns file
  (:require
   [clojure.edn :as edn]
   [v0_1_X.strategy :as strat]
   [v0_2_X.strindicator :as strindy]
   [v0_2_X.config :as config]
   [v0_2_X.hydrate :as hyd]
   [util]))

(def data-folder "data/")

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
  (spit (str data-folder file-name) (prn-str contents) :append append?)))

(defn clear-file [file-name]
  (spit (str data-folder file-name) ""))

(defn delete-by-id [file-name id]
  (let [contents (read-file file-name)
        new-contents (filter #(not= (:id %) id) contents)]
    (clear-file file-name)
    (for [new-content new-contents]
      (write-file file-name new-content))))

(defn get-by-id [file-name id]
  (util/find-in (read-file file-name) :id id))

(defn save-hystrindy-to-file
  ([hystrindy] (save-hystrindy-to-file hystrindy "hystrindies.edn"))
  ([hystrindy file-name]
   (let [formatted-hystrindy 
         (assoc 
          hystrindy 
          :strindy 
          (format-strindy-for-edn 
           (get hystrindy 
            :strindy)))]
     (write-file file-name formatted-hystrindy true))))

(defn save-hystrindies-to-file 
  ([hystrindies] (save-hystrindies-to-file hystrindies "hystrindies.edn"))
  ([hystrindies file-name]
  (for [hyst hystrindies]
    (save-hystrindy-to-file hyst file-name))))

(defn save-streams-to-file 
  ([streams] (save-streams-to-file "streams.edn" streams))
  ([file-name streams]
  (write-file file-name streams true)))

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
  ([] (get-hystrindies-from-file "data/hystrindies.edn"))
  ([file-name]
   (let [formatted-hystrindies (read-file file-name)]
     (for [formatted-hystrindy formatted-hystrindies]
       (deformat-hystrindy formatted-hystrindy)))))



(comment
  (def hystrindies (get-hystrindies-from-file))
  )

(comment
  (def backtest-config (config/get-backtest-config-util
                      ;; ["EUR_USD" "both" "AUD_USD" "inception" "GBP_USD" "inception" "USD_JPY" "inception"]
                        ["EUR_USD" "intention"]
                        "binary" 1 2 3 100 "M1"))

  (def streams (hyd/get-backtest-streams backtest-config))

  (def strindy (strindy/make-strindy-recur (backtest-config :strindy-config)))

  (def hystrindy (hyd/hydrate-strindy strindy streams))

  (save-hystrindy-to-file hystrindy)

  (def hystrindy2 (nth (get-hystrindies-from-file) 3))

  (def strindy2 (:strindy hystrindy2))

  (def sieve-stream (strindy/get-sieve-stream strindy (streams :inception-streams)))
  (def sieve-stream2 (strindy/get-sieve-stream strindy2 (streams :inception-streams)))

  (def return-streams (strindy/get-return-streams-from-sieve sieve-stream (streams :intention-streams)))
  (def return-streams2 (strindy/get-return-streams-from-sieve sieve-stream2 (streams :intention-streams)))
  )