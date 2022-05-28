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

(comment
  "Timed Async Run Oneshot"
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
  "Async scheduled runner"
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
  "Timed Async robustness check oneshot"
  (time
   (let [factory-config (apply config/get-factory-config-util
                         [[["EUR_USD" "both" "GBP_USD" "inception" "EUR_GBP" "inception"]
                          "ternary" 1 2 3 25 25 "M15" "score-x"]
                         [20 0.25 0.2 0.5]
                         0 10])
        file-name (util/config->file-name factory-config)
        file-chan (async/chan)
        watcher-atom (atom 0)]
    (factory/run-factory-to-file-async factory-config file-chan watcher-atom)
    (loop []
      (Thread/sleep 500)
      ;; (println @watcher-atom)
      (if (>= @watcher-atom (-> factory-config :factory-num-produced))
        (do
          (println (arena/get-robustness file-name))
          (file/delete-file (str file/hyst-folder file-name))
          )
        (recur)))
    ))
  )

(comment
  "Timed Synchronus robustness check oneshot"
  (time
   (let [factory-config (apply config/get-factory-config-util
                               [[["EUR_USD" "both"]
                                "ternary" 1 2 3 25 25 "M15" "sharpe"]
                                [20 0.25 0.2 0.5]
                                0 10])
         file-name (util/config->file-name factory-config)]
     (factory/run-factory-to-file factory-config)
     (println (arena/get-robustness file-name))
     (file/delete-file (str file/hyst-folder file-name))
     )))

(comment
  "Speed comparison"
  (time
   (let [factory-config (config/get-factory-config-util
                         [["EUR_USD" "both" "AUD_USD" "inception" "USD_CHF" "inception"
                           "GBP_USD" "inception"]
                          "ternary" 1 4 6 50 50 "M15" "score-x"]
                         [20 0.25 0.2 0.5]
                         4 1)
         file-name (util/config->file-name factory-config)]
     (factory/run-factory-to-file factory-config)
     (println (arena/get-robustness file-name))
     (file/delete-file (str file/hyst-folder file-name)))))


(comment
  "Synchronous Scheduled runner"
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
  "Synchronous oneshot"
  (let [factory-config (config/get-factory-config-util
                        [["AUD_JPY" "both"]
                         "ternary" 1 2 3 50 50 "M15" "score-x"]
                        [10 0.5 0.2 0.5]
                        0 20)
        file-name (util/config->file-name factory-config)]
    (factory/run-factory-to-file factory-config)
    (arena/run-best-gausts file-name)
    (file/delete-file (str file/hyst-folder file-name)))
  )

(comment
  "old-scheduled synchronous runner"
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
  "old-scheduled synchronous runner (no verification)"
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
  "Synchronous oneshot robustness test"
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
  "Original laboratory setup... not working"

  ( ["EUR_JPY" "AUD_CAD"] 
           [[["ternary" "long-only" "short-only"]
             [1 2 3] [2 4 6]]
            [[250 500]]
            ["M15" "M30" "H1"]
            ["balance" "sharpe" "sharpe-per-std" "inv-dd-period" "score-x"]
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