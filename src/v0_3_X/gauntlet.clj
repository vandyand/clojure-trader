(ns v0_3_X.gauntlet
  (:require
   [util :as util]
   [file :as file]
   [v0_2_X.hydrate :as hyd]
   [v0_2_X.plot :as plot]
   [v0_2_X.strindicator :as strindy]
   [stats :as stats]
   [v0_2_X.streams :as streams]))

;; (defn fore-intention-streams [new-streams overlap-ind]
;;   (for [stream (get new-streams :intention-streams)]
;;     (util/subvec-end stream overlap-ind)))

;; (defn fore-inception-streams [new-streams overlap-ind]
;;   (let [new-inception-streams (get new-streams :inception-streams)
;;         new-default-stream (first new-inception-streams)
;;         new-other-streams (rest new-inception-streams)
;;         fore-default-stream (mapv #(+ % overlap-ind 1) (util/subvec-end new-default-stream overlap-ind))]
;;     (into [fore-default-stream]
;;           (for [stream new-other-streams]
;;             (util/subvec-end stream overlap-ind)))))

;; (defn get-fore-streams [new-streams old-streams]
;;   (let [overlap-ind (util/get-overlap-ind (-> old-streams :intention-streams first)
;;                                           (-> new-streams :intention-streams first))]
;;     {:inception-streams (fore-inception-streams new-streams overlap-ind)
;;      :intention-streams (fore-intention-streams new-streams overlap-ind)}))

(defn get-fore-hystrindy [hystrindy]
  (hyd/get-hystrindy-fitness (hyd/hydrate-strindy (:strindy hystrindy) (:backtest-config hystrindy) :fore)))

(defn get-fore-hystrindies [hystrindies]
  (for [hystrindy hystrindies]
    (get-fore-hystrindy hystrindy)))

(defn repopulate-return-stream [rivulet]
  {:rivulet rivulet
   :beck (strindy/rivulet->beck rivulet)})

(defn get-gaustrindy [back-hystrindy fore-hystrindy] 
  (let [g-return-streams (get fore-hystrindy :return-stream)]
    {:id (get back-hystrindy :id)
     :strindy (get back-hystrindy :strindy)
     :return-stream (repopulate-return-stream (-> back-hystrindy :return-stream :rivulet))
     :g-sieve-stream (get fore-hystrindy :sieve-stream)
     :g-return-streams g-return-streams
     :g-fitness (-> g-return-streams :beck last)
     :g-score (stats/z-score
               (-> back-hystrindy :return-stream :rivulet)
               (-> fore-hystrindy :return-stream :rivulet))}))

(defn get-gaustrindies [hystrindies fore-hystrindies]
  (for [n (range (count hystrindies))]
    (let [back-hystrindy (nth hystrindies n)
          fore-hystrindy (nth fore-hystrindies n)]
      (get-gaustrindy back-hystrindy fore-hystrindy))))

(defn run-hyst-gauntlet [back-hystrindy]
  (let [fore-hystrindy (get-fore-hystrindy back-hystrindy)]
    (get-gaustrindy back-hystrindy fore-hystrindy)))

(defn run-hyst-gauntlets
  ;; ([] (apply run-gauntlets (get-hysts-and-streams-at-ind)))
  ([back-hystrindies]
   (let [fore-hystrindies (get-fore-hystrindies back-hystrindies)]
     (get-gaustrindies back-hystrindies fore-hystrindies))))


(comment
  (def hystrindies (file/get-hystrindies-from-file))

  (def fore-hystrindies (get-fore-hystrindies hystrindies))

  (def gaustrindies (get-gaustrindies hystrindies fore-hystrindies))

  (file/save-hystrindies-to-file gaustrindies "gaustrindies.edn")
  )