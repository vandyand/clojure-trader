(ns v0_3_X.gauntlet
  (:require
   [edn]
    [v0_2_X.hydrate :as hyd]
   [stats]))

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


(comment
  (def hystrindies (edn/get-hystrindies-from-file))

  (def back-streams (edn/get-streams-from-file))

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