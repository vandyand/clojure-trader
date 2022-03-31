(ns v0_3_X.gauntlet
  (:require
   [util :as util]
   [file :as file]
   [v0_2_X.hydrate :as hyd]
   [v0_2_X.plot :as plot]
   [stats :as stats]))

(defn fore-intention-streams [new-streams overlap-ind]
  (for [stream (get new-streams :intention-streams)]
    (util/subvec-end stream overlap-ind)))

(defn fore-inception-streams [new-streams overlap-ind]
  (let [new-inception-streams (get new-streams :inception-streams)
        new-default-stream (first new-inception-streams)
        new-other-streams (rest new-inception-streams)
        fore-default-stream (mapv #(+ % overlap-ind 1) (util/subvec-end new-default-stream overlap-ind))] 
    (into [fore-default-stream]
          (for [stream new-other-streams]
            (util/subvec-end stream overlap-ind)))))

(defn get-fore-streams [new-streams old-streams]
  (let [overlap-ind (util/get-overlap-ind (-> old-streams :intention-streams first) 
                                     (-> new-streams :intention-streams first))]
    {:id (.toString (java.util.UUID/randomUUID))
   :inception-streams (fore-inception-streams new-streams overlap-ind)
   :intention-streams (fore-intention-streams new-streams overlap-ind)}))

(defn get-fore-hystrindy [hystrindy fore-streams]
  (hyd/get-hystrindy-fitness (hyd/hydrate-strindy (:strindy hystrindy) fore-streams)))

(defn get-fore-hystrindies [hystrindies fore-streams]
  (for [hystrindy hystrindies]
   (get-fore-hystrindy hystrindy fore-streams)))

(defn get-gaustrindy [back-hystrindy fore-hystrindy]
  (let [g-return-streams (get fore-hystrindy :return-streams)]
    {:id (get back-hystrindy :id)
     :streams-id (get back-hystrindy :streams-id)
     :strindy (get back-hystrindy :strindy)
     :return-streams (get back-hystrindy :return-streams)
     :g-sieve-stream (get fore-hystrindy :sieve-stream)
     :g-return-streams g-return-streams
     :g-fitness (-> g-return-streams first :sum-beck last)
     :g-score (stats/z-score
               (-> back-hystrindy :return-streams first :sum-delta)
               (-> fore-hystrindy :return-streams first :sum-delta))}))

(defn get-gaustrindies [hystrindies fore-hystrindies]
  (for [n (range (count hystrindies))]
   (let [back-hystrindy (nth hystrindies n)
         fore-hystrindy (nth fore-hystrindies n)]
     (get-gaustrindy back-hystrindy fore-hystrindy))))

(defn get-hystses-and-streamses-from-file []
  (let [back-hystrindieses (group-by :streams-id (file/get-hystrindies-from-file "hystrindies.edn"))
        back-streamses (file/read-file "streams.edn")
        new-streamses (for [back-streams back-streamses]
                        (hyd/get-backtest-streams (get back-streams :backtest-config)))]
    [back-hystrindieses back-streamses new-streamses]))

(defn get-hysts-and-streams-at-ind 
  ([] (get-hysts-and-streams-at-ind (get-hystses-and-streamses-from-file)))
  ([hystses-and-streamses] (get-hysts-and-streams-at-ind 
                            hystses-and-streamses 
                            (- (count (second hystses-and-streamses)) 1)))
  ([hystses-and-streamses ind]
  (let [[back-hystrindieses back-streamses new-streamses] hystses-and-streamses
        back-hystrindies (get back-hystrindieses (nth (keys back-hystrindieses) ind))
        back-streams (-> back-streamses (nth ind))
        new-streams (-> new-streamses (nth ind))]
    [back-hystrindies back-streams new-streams])))

(defn run-gauntlet-single [back-hystrindy back-streams new-streams]
  (let [fore-streams (get-fore-streams new-streams back-streams)
        fore-hystrindy (get-fore-hystrindy back-hystrindy fore-streams)]
    (get-gaustrindy back-hystrindy fore-hystrindy)))

(defn run-gauntlet 
  ([] (apply run-gauntlet (get-hysts-and-streams-at-ind)))
  ([back-hystrindies back-streams new-streams]
  (let [fore-streams (get-fore-streams new-streams back-streams)
        fore-hystrindies (get-fore-hystrindies back-hystrindies fore-streams)]
    (get-gaustrindies back-hystrindies fore-hystrindies))))

(defn run-gauntlets []
  (let [[back-hystrindieses back-streamses new-streamses] (get-hystses-and-streamses-from-file)]
    (for [n (range (count back-streamses))]
      (let [back-hystrindies (get back-hystrindieses (nth (keys back-hystrindieses) n))
            back-streams (-> back-streamses (nth n))
            new-streams (-> new-streamses (nth n))]
        (run-gauntlet back-hystrindies back-streams new-streams)))))


(comment
  (def gaustses (run-gauntlets))
  (file/clear-file "gaustrindies.edn")
  (for [gausts gaustses]
    (file/save-hystrindies-to-file (map #(dissoc % :return-streams) gausts) "gaustrindies.edn")))


(comment
  (def hystrindies (file/get-hystrindies-from-file))

  (def back-streams (first (file/read-file "streams.edn")))

  (def new-streams (hyd/get-backtest-streams (get back-streams :backtest-config)))

  (def fore-streams (get-fore-streams new-streams back-streams))

  (def fore-hystrindies (get-fore-hystrindies hystrindies fore-streams))

  (def gaustrindies (get-gaustrindies hystrindies fore-hystrindies))

  (v0_2_X.plot/plot-with-intentions gaustrindies (fore-streams :intention-streams) :g-return-streams)
  )


(comment
  (def stream-hystrindies (group-by :streams-id (file/get-hystrindies-from-file "hystrindies.edn")))

  (def back-streams (file/read-file "streams.edn"))

  (def new-streams (for [back-stream back-streams]
                     (hyd/get-backtest-streams (get back-stream :backtest-config))))

  (def fore-streams (for [n (range (count back-streams))] 
                      (get-fore-streams (nth new-streams n) (nth back-streams n))))

  (def fore-hystrindies (for [n (range (count back-streams))]
                          (get-fore-hystrindies 
                           (get stream-hystrindies (nth (keys stream-hystrindies) n)) 
                           (nth fore-streams n))))

  (def gaustrindies (for [n (range (count back-streams))]
                     (get-gaustrindies 
                      (get stream-hystrindies (nth (keys stream-hystrindies) n)) 
                      (nth fore-hystrindies n))))

  (plot/plot-with-intentions (last gaustrindies) ((last fore-streams) :intention-streams) :g-return-streams)
  )
