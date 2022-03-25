(ns edn
  (:require
   [clojure.edn :as edn]
   [v0_1_X.incubator.strategy :as strat]
   [v0_2_X.strindicator :as strindy]
   [v0_2_X.config :as config]
   [v0_2_X.hydrate :as hyd]))

;; (def backtest-config (config/get-backtest-config-util
;;                       ;; ["EUR_USD" "both" "AUD_USD" "inception" "GBP_USD" "inception" "USD_JPY" "inception"]
;;                       ["EUR_USD" "intention"]
;;                       "binary" 1 2 3 100 "M1"))

;; (def strindy (strindy/make-strindy-recur (backtest-config :strindy-config)))

(defn format-strindy-for-edn [strindy]
  (clojure.walk/postwalk
   (fn [form]
     (if (and (map? form) (some #(= % :policy) (keys form)))
       (update-in form [:policy] dissoc :fn)
       form))
   strindy))

(defn save-hystrindy-to-file
  ([hystrindy] (save-hystrindy-to-file "data.edn" hystrindy))
  ([file-name hystrindy]
   (let [formatted-hystrindy (assoc hystrindy :strindy (format-strindy-for-edn (hystrindy :strindy)))]
     (spit file-name (prn-str formatted-hystrindy) :append true))))


(defn deformat-hystrindy [formatted-hystrindy]
  (clojure.walk/postwalk
   (fn [form]
     (if (and (map? form) (some #(= % :policy) (keys form)))
       (let [form-type (get-in form [:policy :type])
             func (cond (= form-type "rand")
                        (constantly (get-in form [:policy :value]))
                        (some #(= % :tree) (keys (form :policy)))
                        (fn [& args] (strat/solve-tree (get-in form [:policy :tree]) args))
                        :else (:fn (reduce (fn [acc cur-val] (when (= (:type cur-val) form-type) (reduced cur-val)))
                                           nil strindy/strindy-funcs)))]
         (assoc form :policy (into (:policy form) {:fn func})))
       form))
   formatted-hystrindy))

(defn get-hystrindies-from-file
  ([] (get-hystrindies-from-file "data.edn"))
  ([file-name]
   (let [formatted-hystrindies (edn/read-string (clojure.string/replace (str "[" (slurp "data.edn") "]") #"\n" ""))]
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