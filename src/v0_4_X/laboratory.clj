(ns v0_4_X.laboratory
  (:require
   [v0_3_X.arena :as arena]
   [config :as config]
   [file :as file]
   [v0_2_X.hyst_factory :as factory]
   [clojure.core.async :as async]
   [util :as util]
   [v0_3_X.gauntlet :as gaunt]
   [helpers :as hlp]
   [env :as env]
   [api.oanda_api :as oa]))

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
                              [["EUR_GBP" "both"]
                               "ternary" 1 4 6 500 500 "H1" "score-x"]
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
         (recur))))))

;; factory-config (config/get-factory-config-util
;;                         [["EUR_USD" "both"]
;;                          "ternary" 1 4 6 500 500 "H1" "score-x"]
;;                         [20 0.25 0.2 0.5]
;;                         3 250)

(comment
  "misc"
  (time
   (let [factory-config (apply config/get-factory-config-util
                                    [[["AUD_USD" "both" "EUR_USD" "both" "EUR_AUD" "both"]
                                      "ternary" 1 2 3 50 500 "H1" "score-x"]
                                     [10 0.1 0.2 0.5]
                                     0 100])
        ;; file-name (util/config->file-name factory-config)
         factory-chan (async/chan)
        ;; watcher-atom (atom 0)
         ]
     (factory/run-factory-async factory-config factory-chan)
    ;;  (arena/run-best-gausts-async factory-chan)
     (arena/get-robustness-async factory-chan)
     ))

  (arena/get-robustness "H1-500-T_AUD_USD.edn")
  (arena/run-best-gausts "H1-500-T_AUD_USD.edn")
  )


(comment
  "Fully Async scheduled runner"
  (let [schedule-chan (async/chan)
        future-times (util/get-future-unix-times-sec "H1")]

    (util/put-future-times schedule-chan future-times)

    (async/go-loop []
      (when-some [val (async/<! schedule-chan)]
        (let [factory-config (apply config/get-factory-config-util
                                    [[["AUD_USD" "both"]
                                      "ternary" 1 2 3 250 750 "H1" "score-x"]
                                     [10 0.25 0.2 0.5]
                                     0 200])
              factory-chan (async/chan)]
          (factory/run-factory-async factory-config factory-chan)
          (arena/run-best-gausts-async factory-chan)))
      (when (not (env/get-env-data :KILL_GO_BLOCKS?)) (recur))))
  )

(comment
 (doseq [instrument ["EUR_USD"]]
        ;; (doseq [instrument ["AUD_USD" "EUR_USD" "EUR_AUD"]]
          (async/go
            (let [factory-config (apply config/get-factory-config-util
                                        [[[instrument "both"]
                                          "ternary" 1 2 4 150 3000 "H2" "score-x"]
                                         [10 0.4 0.1 0.5]
                                         1 200])
                  factory-chan (async/chan)]
              (factory/run-factory-async factory-config factory-chan)
              (arena/run-best-gausts-async factory-chan)
              ;; (arena/get-robustness-async factory-chan)
              ))))

(comment
  "Fully Async Multi-currency scheduled runner"
  (let [schedule-chan (async/chan)
        future-times (util/get-future-unix-times-sec "M5")]

    (util/put-future-times schedule-chan future-times)

    (async/go-loop []
      (when-some [val (async/<! schedule-chan)]
        (doseq [instrument ["EUR_USD"]]
          (async/go
            (let [factory-config (apply config/get-factory-config-util
                                        [[[instrument "both"]
                                          "ternary" 1 2 3 150 1500 "M5" "score-x"]
                                         [20 0.4 0.1 0.5]
                                         0 600]) ;; SOLUTION: Make each of these 600 (or however many) run in parallel (that is, on the gpu)
                  ;; This would mean a rewrite of almost everything... including the GA... This is the idea though isn't it?
                  ;; REDESIGN from ground up for massive parallelization.
                  factory-chan (async/chan)]
              (factory/run-factory-async factory-config factory-chan)
              (arena/run-best-gausts-async factory-chan)
              ;; (arena/get-robustness-async factory-chan)
              ))))
      (when (not (env/get-env-data :KILL_GO_BLOCKS?)) (recur)))))

(comment
  "Fully Async Multi-currency scheduled runner"
  (let [schedule-chan (async/chan)
        future-times (util/get-future-unix-times-sec "H4")]

    (util/put-future-times schedule-chan future-times)

    (async/go-loop []
      (when-some [val (async/<! schedule-chan)]
        (doseq [instrument ["EUR_USD" "USD_JPY" "EUR_GBP" "AUD_USD" "EUR_JPY" "GBP_USD"
                            "USD_CHF" "AUD_JPY" "USD_CAD" "ZAR_JPY" "CHF_JPY" "EUR_CHF"
                            "NZD_USD" "EUR_CAD" "NZD_JPY" "AUD_CHF" "CAD_JPY" "CAD_CHF"]]
        ;; (doseq [instrument ["AUD_USD" "EUR_USD" "EUR_AUD"]]
          (async/go
            (let [factory-config (apply config/get-factory-config-util
                                        [[[instrument "both"]
                                          "ternary" 1 2 3 454 4545 "H4" "score-x"]
                                         [10 0.4 0.1 0.5]
                                         1 200])
                  factory-chan (async/chan)]
              (factory/run-factory-async factory-config factory-chan)
              (arena/run-best-gausts-async factory-chan)
              ;; (arena/get-robustness-async factory-chan)
              ))))
      (when (not (env/get-env-data :KILL_GO_BLOCKS?)) (recur)))))

(comment
  "Async scheduled runner"
  (let [schedule-chan (async/chan)
        future-times (util/get-future-unix-times-sec "M1" 24)]

    (util/put-future-times schedule-chan future-times)

    (async/go-loop []
      (when-some [val (async/<! schedule-chan)]
        (let [factory-config (apply config/get-factory-config-util
                         [[["EUR_AUD" "both"]
                          "ternary" 1 2 3 250 25 "M1" "score-x"]
                         [10 0.25 0.2 0.5]
                         0 100])
              file-name (util/config->file-name factory-config)
              file-chan (async/chan)
              watcher-atom (atom 0)]
          (factory/run-factory-to-file-async factory-config file-chan watcher-atom)
          ;; (loop []
            ;; (Thread/sleep 1000)
            (if (>= @watcher-atom (-> factory-config :factory-num-produced))
              (do
                (arena/run-best-gausts file-name)
                (file/delete-file (str file/hyst-folder file-name)))
              (recur))
          ;; )
          ))
      (recur)))
  )

(comment
  "Timed Async robustness check oneshot"
  (time
   (let [factory-config (apply config/get-factory-config-util
                         [[["EUR_USD" "both"]
                          "ternary" 1 2 3 250 25 "M1" "score-x"]
                         [10 0.25 0.2 0.5]
                         0 100])
        file-name (util/config->file-name factory-config)
        file-chan (async/chan)
        watcher-atom (atom 0)]
    (factory/run-factory-to-file-async factory-config file-chan watcher-atom)
    (loop []
      (Thread/sleep 100)
      ;; (println @watcher-atom)
      (if (>= @watcher-atom (-> factory-config :factory-num-produced))
        (do
          ;; (println (arena/get-robustness file-name))
          (println (arena/run-best-gausts file-name))
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