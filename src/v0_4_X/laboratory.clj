(ns v0_4_X.laboratory
  (:require
   [v0_3_X.arena :as arena]
   [config :as config]
   [file :as file]
   [v0_2_X.hyst_factory :as factory]
   [clojure.core.async :as async]
   [util :as util]
   [v0_3_X.gauntlet :as gaunt]))

(defn parse-config-arg-ranges [config-arg-ranges]
  )

(defn run-lab [configs]
  (doseq [config configs]
    (let [factory-config (apply config/get-factory-config-util config)]
    (factory/run-factory-to-file factory-config)
    (arena/get-robustness (util/config->file-name factory-config)))))

;; (defn feed-forward-test []
;;   (let [factory-config (config/get-factory-config-util
;;                           [["AUD_JPY" "both"]
;;                            "ternary" 1 2 3 250 500 "M15" "score-x"]
;;                           [10 0.5 0.2 0.5]
;;                           0 200)
;;           file-name (util/config->file-name factory-config)]
;;       (factory/run-factory-to-file factory-config)
;;       (arena/run-best-gausts file-name)
;;       (file/delete-file (str file/hyst-folder file-name)))
;;   )

(comment
  (time
   (let [factory-config (config/get-factory-config-util
                         [["EUR_JPY" "both"]
                          "ternary" 1 4 6 500 500 "H1" "score-x"]
                         [20 0.25 0.2 0.5]
                         3 1000)
         file-name (util/config->file-name factory-config)
         file-chan (async/chan)
         watcher-atom (atom 0)]
     (factory/run-factory-to-file-async factory-config file-chan watcher-atom)
     (loop []
       (Thread/sleep 1000)
       (if (>= @watcher-atom (-> factory-config :factory-num-produced))
         (do
           (arena/run-best-gausts file-name)
           (file/delete-file (str file/hyst-folder file-name)))
         (recur))))))

(comment
  "Async factory runner"
  (def schedule-chan (async/chan))

  (def future-times (util/get-future-unix-times-sec "M15" 24))

  (util/put-future-times schedule-chan future-times)

  (async/go-loop []
    (when-some [val (async/<! schedule-chan)]
      (let [factory-config (config/get-factory-config-util
                            [["AUD_JPY" "both"]
                             "ternary" 1 4 6 500 500 "M15" "score-x"]
                            [20 0.25 0.2 0.5]
                            3 250)
            file-name (util/config->file-name factory-config)
            file-chan (async/chan)
            watcher-atom (atom 0)]
        (factory/run-factory-to-file-async factory-config file-chan watcher-atom)
        (loop []
          (Thread/sleep 1000)
          (if (>= @watcher-atom (-> factory-config :factory-num-produced))
            (do
              (arena/run-best-gausts file-name)
              (file/delete-file (str file/hyst-folder file-name)))
            (recur)))))
    (recur))

  (async/close! schedule-chan)

  )

(comment
  "Another async factory test"
  (time
   (let [factory-config (config/get-factory-config-util
                        [["EUR_JPY" "both"]
                         "ternary" 1 4 6 500 500 "M15" "score-x"]
                        [20 0.25 0.2 0.5]
                        3 10)
        file-name (util/config->file-name factory-config)
        file-chan (async/chan)
        watcher-atom (atom 0)]
    (factory/run-factory-to-file-async factory-config file-chan watcher-atom)
    (loop []
      (Thread/sleep 1000)
      (println @watcher-atom)
      (if (>= @watcher-atom (-> factory-config :factory-num-produced))
        (do
          (arena/run-best-gausts file-name)
          (file/delete-file (str file/hyst-folder file-name)))
        (recur)))
    ))
  )

(comment
  "Speed comparison"
  (time
   (let [factory-config (config/get-factory-config-util
                            [["EUR_JPY" "both"]
                             "ternary" 1 4 6 50 50 "M15" "score-x"]
                            [10 0.25 0.2 0.5]
                            3 200)
            file-name (util/config->file-name factory-config)]
        (factory/run-factory-to-file factory-config)
        (arena/run-best-gausts file-name)
        (file/delete-file (str file/hyst-folder file-name)))))


(comment
  "Scheduled runner (synchronous factory)"
  (def schedule-chan (async/chan))
  
  (def future-times (util/get-future-unix-times-sec "M15" 26))
  
  (util/put-future-times schedule-chan future-times)
  
  (async/go-loop []
    (when-some [val (async/<! schedule-chan)]
      (let [factory-config (config/get-factory-config-util
                            [["AUD_JPY" "both"]
                             "ternary" 1 4 6 500 500 "M15" "score-x"]
                            [20 0.25 0.2 0.5]
                            3 250)
            file-name (util/config->file-name factory-config)]
        (factory/run-factory-to-file factory-config)
        (arena/run-best-gausts file-name)
        (file/delete-file (str file/hyst-folder file-name)))
      )
    (recur))
  
  (async/close! schedule-chan)
  )


(comment
  "This works"
  (async/go-loop []
    (let [factory-config (config/get-factory-config-util
                          [["AUD_JPY" "both"]
                           "ternary" 1 2 3 250 500 "M15" "score-x"]
                          [10 0.5 0.2 0.5]
                          0 200)
          file-name (util/config->file-name factory-config)]
      (factory/run-factory-to-file factory-config)
      (arena/run-best-gausts file-name)
      (file/delete-file (str file/hyst-folder file-name))
      (Thread/sleep 280000))
    (recur))
  )

(comment
  "works for hysts (no fore robustness checking)"
  (async/go-loop []
    (let [factory-config  (config/get-factory-config-util
                           [["AUD_JPY" "both"]
                            "ternary" 1 2 3 250 500 "M15" "score-x"]
                           [10 0.5 0.2 0.5]
                           1 100)
          hysts (factory/run-factory factory-config)]
      (arena/post-hysts hysts))
    (Thread/sleep (* 1000 60 60))
    (recur))
  )



(comment
  (async/go-loop []
    (let [factory-config (config/get-factory-config-util
                          [["AUD_JPY" "both"]
                           "ternary" 1 2 3 500 0 "M15" "sharpe-per-std"]
                          [10 0.5 0.2 0.5]
                          0 500)
          robust-hysts (factory/run-checked-factory factory-config)]
      (arena/post-gausts (gaunt/run-gauntlet robust-hysts)))
    (Thread/sleep 900000)
    (recur))
  )


(comment
  "Testing robustness"
  (do
    (def factory-config (config/get-factory-config-util
                         [["AUD_JPY" "both"]
                          "ternary" 1 2 3 250 250 "M15" "score-x"]
                         [10 0.5 0.2 0.5]
                         0 100))
    (factory/run-factory-to-file factory-config)
    (println (arena/get-robustness (util/config->file-name factory-config)))
    (file/delete-file (str file/hyst-folder (util/config->file-name factory-config))))
  )


(comment

  ( ["EUR_JPY" "AUD_CAD"] 
           [[["ternary" "long-only" "short-only"]
             [1 2 3] [2 4 6]]
            [[250 500]]
            ["M15" "M30" "H1"]
            ["balance" "sharpe" "sharpe-per-std" "inv-max-dd-period" "score-x"]
            [[25 0.5 0.2 0.5] [25 0.2 0.6 0.2] [25 0.2 0.1 0.7] [25 0.8 0.8 0.1] [25 0.8 0.2 0.6]]
            [10 20]
            5])
  
  (def factory-config (config/get-factory-config-util
                       [["CAD_SGD" "inception" "AUD_CAD" "inception"
                         "AUD_CHF" "inception" "EUR_USD" "inception"
                         "EUR_JPY" "inception" "EUR_GBP" "inception"
                         "GBP_USD" "inception" "AUD_USD" "both"]
                        "ternary" 1 2 3 250 500 "M15" "score-x"]
                       [30 0.5 0.2 0.5]
                       10 20))
  (factory/run-factory-to-file factory-config))