(ns v0_2_X.streams
  (:require
   [file :as file]
   [util :as util]
   [v0_2_X.config :as config]
   [v0_2_X.strindicator :as strindy]
   [v0_2_X.oanda_strindicator :as ostrindy]))

(defn get-instrument-file-name [instrument-config]
  (str "streams/" (get instrument-config :name) "-" (get instrument-config :granularity) ".edn"))

(defn up-to-date? [time-stamp granularity]
  (< (util/current-time-sec) (+ time-stamp (util/granularity->seconds granularity))))

(defn update-stream-file
  ([instrument-config old-stream]
   (let [file-name (get-instrument-file-name instrument-config)
         new-stream (ostrindy/get-instrument-stream (assoc instrument-config :count 5000))
         overlap-ind (util/get-overlap-ind old-stream new-stream)
         updated-stream (into old-stream (util/subvec-end new-stream overlap-ind))]
     (file/write-file
      file-name
      {:time-stamp (util/current-time-sec)
       :stream updated-stream}
      false))))

(defn get-stream-from-file-or-api [instrument-config]
  (let [file-name (get-instrument-file-name instrument-config)
        file-exists (.exists (clojure.java.io/file (str file/data-folder file-name)))
        file-content (when file-exists (first (file/read-file file-name)))
        up-to-date? (when file-content (up-to-date? (get file-content :time-stamp) (get instrument-config :granularity)))]
    (if file-content
      (if up-to-date?
        (util/subvec-end (vec (get file-content :stream)) (get instrument-config :count))
        (do
          (update-stream-file instrument-config (get file-content :stream))
          (get-stream-from-file-or-api instrument-config)))
      (let [stream (ostrindy/get-instrument-stream (assoc instrument-config :count 5000))]
        (file/write-file
         file-name
         {:time-stamp (util/current-time-sec)
          :stream stream})
        (util/subvec-end stream (get instrument-config :count))))))

(defn fetch-streams [backtest-config]
  (let [instruments-config (ostrindy/get-instruments-config backtest-config)]
    (doall
     (for [instrument-config instruments-config]
       {:instrument (get instrument-config :name)
        :stream (get-stream-from-file-or-api instrument-config)}))))

(defn get-incint-streams [backtest-config streams incint]
  (let [init-stream (if (= incint "inception") [(vec (range (get backtest-config :num-data-points)))] [])]
    (into
     init-stream
     (map (fn [valid-stream-config]
            (get (util/find-in streams :instrument (get valid-stream-config :name)) :stream))
          (filter
           (fn [stream-config] 
             (and
              (not= (get stream-config :name) "default")
              (not= (get stream-config :incint)
                   (if (= incint "inception") "intention" "inception"))))
           (get backtest-config :streams-config))))))

(comment
  (def backtest-config (config/get-backtest-config-util
                        ["EUR_USD" "both" "AUD_USD" "both" "GBP_USD" "inception" "USD_JPY" "inception"]
                        ;; ["EUR_USD" "intention"]
                        "binary" 1 2 3 100 "M1"))

  (def streams (fetch-streams backtest-config))

  (def strindy (strindy/make-strindy (backtest-config :strindy-config)))

  (def sieve-stream (strindy/get-sieve-stream strindy (get-incint-streams backtest-config streams "inception")))

  (def return-streams (strindy/get-return-streams-from-sieve sieve-stream (get-incint-streams backtest-config streams "intention"))))
