(ns v0_3_X.gauntlet
  (:require
   [file :as file]
    [v0_2_X.hydrate :as hyd]
   [stats :as stats]))

(defn get-overlap-ind [old new]
  (loop [i 0]
    (cond
      (>= i (count new)) -1
      (let [sub-new (subvec new 0 (- (count new) i))
            sub-old (subvec old (- (count old) (count sub-new)))]
        (= sub-old sub-new))
      i
      :else (recur (inc i)))))

(defn get-fore-series [new overlap-ind]
  (subvec new (- (count new) overlap-ind)))


(defn fore-intention-streams [new-streams overlap-ind]
  (for [stream (get new-streams :intention-streams)]
    (get-fore-series stream overlap-ind)))

(defn fore-inception-streams [new-streams overlap-ind]
  (let [new-inception-streams (get new-streams :inception-streams)
        new-default-stream (first new-inception-streams)
        new-other-streams (rest new-inception-streams)
        fore-default-stream (mapv #(+ % overlap-ind 1) (get-fore-series new-default-stream overlap-ind))] 
    (into [fore-default-stream]
          (for [stream new-other-streams]
            (get-fore-series stream overlap-ind)))))

(defn get-fore-streams [new-streams overlap-ind]
  {:id (.toString (java.util.UUID/randomUUID))
   :inception-streams (fore-inception-streams new-streams overlap-ind)
   :intention-streams (fore-intention-streams new-streams overlap-ind)})

(defn get-fore-hystrindies [hystrindies fore-streams]
  (for [hystrindy hystrindies]
   (hyd/get-hystrindy-fitness (hyd/hydrate-strindy (:strindy hystrindy) fore-streams))))

(defn get-ghystrindies [hystrindies fore-hystrindies]
  (for [n (range (count hystrindies))]
   (let [back-hystrindy (nth hystrindies n)
         fore-hystrindy (nth fore-hystrindies n)
         return-streams (get fore-hystrindy :return-streams)]
     (assoc back-hystrindy
            :g-return-streams return-streams
            :g-fitness (-> return-streams first :sum-beck last)
            :g-score (stats/z-score
                      (-> back-hystrindy :return-streams first :sum-delta)
                      (-> fore-hystrindy :return-streams first :sum-delta))))))

(defn run-gauntlet []
  (let [back-hystrindies (file/get-hystrindies-from-file "data.edn")
        back-streams (first (file/read-file "streams.edn"))
        new-streams (hyd/get-backtest-streams (get back-streams :backtest-config))
        overlap-ind (let [new (first (get new-streams :intention-streams))
                          old (first (get back-streams :intention-streams))]
                      (get-overlap-ind old new))
        fore-streams (get-fore-streams new-streams overlap-ind)
        fore-hystrindies (get-fore-hystrindies back-hystrindies fore-streams)]
    (get-ghystrindies back-hystrindies fore-hystrindies)))

(comment
  (def ghystrindies (run-gauntlet))
  )

(comment
  (def hystrindies (file/get-hystrindies-from-file))

  (def back-streams (first (file/read-file "streams.edn")))

  (def new-streams (hyd/get-backtest-streams (get back-streams :backtest-config)))

  (def overlap-ind
    (let [new (first (get new-streams :intention-streams))
          old (first (get back-streams :intention-streams))]
      (get-overlap-ind old new)))

  (def fore-streams (get-fore-streams new-streams overlap-ind))

  (def fore-hystrindies (get-fore-hystrindies hystrindies fore-streams))

  (def ghystrindies (get-ghystrindies hystrindies fore-hystrindies))

  (v0_2_X.plot/plot-with-intentions ghystrindies (fore-streams :intention-streams) :g-return-streams)
  )


(comment
  (def stream-hystrindies (group-by :streams-id (file/get-hystrindies-from-file "data.edn")))

  (def back-streams (file/read-file "streams.edn"))

  (def new-streams (for [back-stream back-streams]
                     (hyd/get-backtest-streams (get back-stream :backtest-config))))

  (def overlap-inds
    (for [n (range (count back-streams))]
     (let [new (-> new-streams (nth n) :intention-streams first)
          old (-> back-streams (nth n) :intention-streams first)]
      (get-overlap-ind old new))))

  (def fore-streams (for [n (range (count back-streams))] 
                      (get-fore-streams (nth new-streams n) (nth overlap-inds n))))

  (def fore-hystrindies (for [n (range (count back-streams))]
                          (get-fore-hystrindies 
                           (get stream-hystrindies (nth (keys stream-hystrindies) n)) 
                           (nth fore-streams n))))

  (def ghystrindies (for [n (range (count back-streams))]
                     (get-ghystrindies 
                      (get stream-hystrindies (nth (keys stream-hystrindies) n)) 
                      (nth fore-hystrindies n))))

  (v0_2_X.plot/plot-with-intentions (second ghystrindies) ((second fore-streams) :intention-streams) :g-return-streams)
  )
