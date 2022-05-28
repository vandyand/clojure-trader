(ns v0_3_X.gauntlet
  (:require
   [file :as file]
   [v0_2_X.hydrate :as hyd]
   [v0_2_X.strindicator :as strindy]
   [stats :as stats]
   ))

(defn good-gaust? [gaust]
  (> (:z-score gaust) -0.25))

(defn get-best-gausts [gausts]
   (filterv good-gaust? gausts))

(defn get-best-gaust [gausts]
  (reduce (fn [acc cur] (if (> (:z-score cur) (:z-score acc)) cur acc)) gausts))

(defn get-fore-hystrindy [hystrindy]
  (hyd/get-hystrindy-fitness (hyd/hydrate-strindy (:strindy hystrindy) (:backtest-config hystrindy) nil :fore)))

(defn get-fore-hystrindies [hystrindies]
  (for [hystrindy hystrindies]
    (get-fore-hystrindy hystrindy)))

(defn repopulate-return-stream [rivulet]
  {:rivulet rivulet
   :beck (strindy/rivulet->beck rivulet)})

(defn get-gaustrindy [back-hystrindy fore-hystrindy] 
  (let [g-return-stream (get fore-hystrindy :return-stream)
        z-score (stats/z-score
                 (-> back-hystrindy :return-stream :rivulet)
                 (-> fore-hystrindy :return-stream :rivulet))]
    {:id (get back-hystrindy :id)
     :strindy (get back-hystrindy :strindy)
     :streams-config (-> back-hystrindy :backtest-config :streams-config)
     :return-stream (repopulate-return-stream (-> back-hystrindy :return-stream :rivulet))
     :g-sieve-stream (get fore-hystrindy :sieve-stream)
     :g-return-stream g-return-stream
     :g-fitness (-> g-return-stream :beck last)
     :z-score z-score
     :g-score (* z-score (-> back-hystrindy :fitness))}))

(defn get-gaustrindies [hystrindies fore-hystrindies]
  (for [n (range (count hystrindies))]
    (let [back-hystrindy (nth hystrindies n)
          fore-hystrindy (nth fore-hystrindies n)]
      (get-gaustrindy back-hystrindy fore-hystrindy))))

(defn run-gauntlet 
  "arg is either vector of hysts or string file-name of hysts file"
  [arg]
  (let [hysts (if (= (type arg) java.lang.String) (file/get-hystrindies-from-file arg) arg)
        fysts (get-fore-hystrindies hysts)
        gausts (get-gaustrindies hysts fysts)]
    gausts))

(defn run-guantlet-single [hyst]
  (let [fyst (get-fore-hystrindy hyst)]
    (get-gaustrindy hyst fyst)))

(comment
  (def hysts (file/get-hystrindies-from-file))

  (def fysts (get-fore-hystrindies hysts))

  (def gausts (get-gaustrindies hysts fysts))

  (file/save-hystrindies-to-file gausts)
  )