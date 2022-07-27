(ns v0_2_X.solver
  (:require
   [util :as util]))

(defn strindy-fn [input-vals]
  (> (+ (first input-vals) (second input-vals)) (+ (nth input-vals 2) (nth input-vals 3))))

(defn get-stream-by-id [streams id]
  (-> (filter #(= (% :id) id) streams) first :stream))

(defn get-input-vals [streams inputs ind]
  (for [input inputs]
    (let [stream (get-stream-by-id streams (input :id))
          true-ind (util/pos-or-zero (- ind (input :shift)))]
      (get stream true-ind))))

(defn solver [streams inputs]
  (for [ind (-> streams first :stream count range)]
    (let [input-vals (get-input-vals streams inputs ind)]
      (-> input-vals strindy-fn util/bool->binary))))

(comment
  (def streams [{:id 0 :stream [1.015 1.016 1.019 1.018 1.017 1.015 1.018 1.02 1.022]}])
  (def inputs [{:id 0 :shift 0} {:id 0 :shift 1} {:id 0 :shift 2} {:id 0 :shift 3}])
  (solver streams inputs))

(defn solve-strindy-at-ind [strindy inc-streams ind]
  (if (contains? strindy :id)
    (let [stream-id (get strindy :id)
          target-stream (get inc-streams stream-id)
          target-stream-ind (util/pos-or-zero (- ind (or (get strindy :shift) 0)))]
      (get-in target-stream [target-stream-ind (get strindy :key)]))
    (let [strind-fn (get-in strindy [:policy :fn])
          strind-inputs (get strindy :inputs)]
      (if (number? strind-fn) strind-fn
          (let [solution
                (apply
                 strind-fn
                 (mapv #(solve-strindy-at-ind % inc-streams ind) strind-inputs))]
            (if (Double/isNaN solution) 0.0 solution))))))

(defn strindy->sieve [strindy inc-streams]
  (vec
   (for [ind (-> inc-streams first count range)]
    (solve-strindy-at-ind strindy inc-streams ind))))

(comment
  (require '[config :as config]
           '[v0_2_X.strindicator :as strindy]
           '[v0_2_X.streams :as streams])
  
  (def backtest-config (config/get-backtest-config-util
                        ["EUR_USD" "both"]
                        "ternary" 1 2 3 4500 "H4"))

  (def streams (streams/fetch-formatted-streams backtest-config))

  (def strindy (strindy/make-strindy (config/get-strindy-config "ternary" 1 2 4 [0] [0])))

  (time (strindy->sieve strindy (streams :inception-streams)))
  
  (time (strindy/get-sieve-stream strindy (streams :inception-streams)))
  )



(comment
  
  ;; Streams example: only inception-streams is passed into strindy->sieve from hydrate
  {:inception-streams
   [[{:v 6433, :o 1.02196, :h 1.02332, :l 1.0216, :c 1.02302}
     {:v 11520, :o 1.02302, :h 1.02502, :l 1.02232, :c 1.02257}
     {:v 20504, :o 1.02259, :h 1.02363, :l 1.02023, :c 1.0208}
     {:v 29780, :o 1.02082, :h 1.02083, :l 1.01162, :c 1.01485}
     {:v 29575, :o 1.01483, :h 1.0153, :l 1.01076, :c 1.01272}
     {:v 12066, :o 1.01268, :h 1.01329, :l 1.01141, :c 1.01174}
     {:v 7260, :o 1.01164, :h 1.01443, :l 1.01156, :c 1.01404}
     {:v 12206, :o 1.01401, :h 1.01524, :l 1.0137, :c 1.01508}
     {:v 19900, :o 1.01508, :h 1.01588, :l 1.01277, :c 1.01418}
     {:v 21118, :o 1.01417, :h 1.0172, :l 1.01384, :c 1.0143}
     {:v 23687, :o 1.01432, :h 1.01525, :l 1.00968, :c 1.01111}
     {:v 3609, :o 1.01113, :h 1.01431, :l 1.01113, :c 1.01392}]],
   :intention-streams
   [[{:v 6433, :o 1.02196, :h 1.02332, :l 1.0216, :c 1.02302}
     {:v 11520, :o 1.02302, :h 1.02502, :l 1.02232, :c 1.02257}
     {:v 20504, :o 1.02259, :h 1.02363, :l 1.02023, :c 1.0208}
     {:v 29780, :o 1.02082, :h 1.02083, :l 1.01162, :c 1.01485}
     {:v 29575, :o 1.01483, :h 1.0153, :l 1.01076, :c 1.01272}
     {:v 12066, :o 1.01268, :h 1.01329, :l 1.01141, :c 1.01174}
     {:v 7260, :o 1.01164, :h 1.01443, :l 1.01156, :c 1.01404}
     {:v 12206, :o 1.01401, :h 1.01524, :l 1.0137, :c 1.01508}
     {:v 19900, :o 1.01508, :h 1.01588, :l 1.01277, :c 1.01418}
     {:v 21118, :o 1.01417, :h 1.0172, :l 1.01384, :c 1.0143}
     {:v 23687, :o 1.01432, :h 1.01525, :l 1.00968, :c 1.01111}
     {:v 3609, :o 1.01113, :h 1.01431, :l 1.01113, :c 1.01392}]]}
  
  ;; strindy example
  {:policy {:type "strategy", 
            :tree [#{0 1} 0 -1], 
            :fn #function[v0-2-X.strindicator/make-strindy-recur/fn--42656]},
 :inputs [{:id 0, :key :o, :shift 6} 
          {:id 0, :key :l, :shift 13}]}
  )


