(ns v0-2-x.straticator)

(comment

  (def num-data-points 10)

  (defn sum [& args] (apply + args))

  (def straticator {:straticator-fn
                    {:inputs [{:id 0}
                              {:straticator-fn
                               {:inputs [{:id 0 :shift 0}]
                                :fn #(+ 1 %)}}
                              {:straticator-fn
                               {:inputs [{:id 0}
                                         {:straticator-fn
                                          {:inputs [{:id 0 :shift 0}]
                                           :fn #(+ % 1)}}]
                                :fn #(+ 1 %1 %2)}}]
                     :fn sum}

                    :subscription-inputs
                    {0 (vec (range num-data-points))}})

  (defn get-subscription-stream-val [stream-id ind]
    ((vec (get-in straticator [:subscription-inputs stream-id])) ind))

  (defn pos-or-zero [num] (if (pos? num) num 0))

  (defn solve-straticator [straticator ind]
    (if (contains? straticator :id)
      (let [stream-id (get straticator :id)
            target-ind (pos-or-zero (- ind (or (get straticator :shift) 0)))]
        (get-subscription-stream-val stream-id target-ind))
      (let [stcr-fn (get-in straticator [:straticator-fn :fn])
            stcr-inputs (get-in straticator [:straticator-fn :inputs])]
        (apply stcr-fn (mapv #(solve-straticator % ind) stcr-inputs)))))

  (map (partial solve-straticator straticator) (range num-data-points)))


