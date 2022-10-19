(ns v0_2_X.streams
  (:require
   [file :as file]
   [util :as util]
   [config :as config]
   [v0_2_X.strindicator :as strindy]
   [api.util :as api_util]
   [api.instruments :as instruments]))

(defn get-instrument-file-name ([instrument-config]
                                (str "streams/" (get instrument-config :name) "-" (get instrument-config :granularity) ".edn"))
  ([name granularity] (str "streams/" name "-" granularity ".edn")))

(defn in-time-window? [time-stamp granularity]
  ;;TODO: UPDATE THIS LOGIC SO IT WORKS CORRECTLY
  (< (util/current-time-sec)
     (+ time-stamp (* 0.5 (util/granularity->seconds granularity)))))

(defn get-api-stream [instrument-config]
  (instruments/get-instrument-stream (assoc instrument-config :count 5000)))

;;if file does not exist -> make new file and populate with data from api and return data
;;else (if file does exist)...
;;    if file is up to date -> read file content and return the stream
;;    else (if file is not up to date)...
;;        delete the file.
;;        recur.

(defn create-stream-file [file-name instrument-config]
  (let [api-stream (get-api-stream instrument-config)]
    (file/write-file
     (str file/data-folder file-name)
     {:time-stamp (util/current-time-sec)
      :stream api-stream})
    api-stream))

(defn get-whole-stream
  [instrument-config]
  (let [file-name (get-instrument-file-name instrument-config)
        file-exists (.exists (clojure.java.io/file (str file/data-folder file-name)))]
    (if (not file-exists)
      (create-stream-file file-name instrument-config)
      (let [file-content (when file-exists (first (file/read-data-file file-name)))
            up-to-date?
            (when file-content
              (in-time-window? (get file-content :time-stamp)
                               (get instrument-config :granularity)))]
        (if up-to-date?
          (vec (:stream file-content))
          (do (file/delete-file file-name)
              ;; (println "deleting file " file-name)
              ;; (Thread/sleep 1000)
              (get-whole-stream instrument-config)))))))

(defn fetch-streams
  ([backtest-config] (fetch-streams backtest-config false))
  ([backtest-config fore?]
   (let [instruments-config (api_util/get-instruments-config backtest-config)
         num-data-points (if (and fore? (get backtest-config :stream-proxy))
                           (util/get-fore-ind (get backtest-config :stream-proxy)
                                              (mapv :o (get-whole-stream (first instruments-config))))
                           (get backtest-config :num-data-points))
         shift-data-points (if fore? 0 (-> backtest-config :shift-data-points))]
     (for [instrument-config instruments-config]
       (let [whole-stream (get-whole-stream instrument-config)
             whole-stream-count (count whole-stream)
             stream (subvec
                     whole-stream
                     (- whole-stream-count
                        num-data-points
                        shift-data-points)
                     (- whole-stream-count
                        shift-data-points))]
         {:instrument (get instrument-config :name)
          :stream stream})))))

(defn get-incint-streams [backtest-config streams incint fore?]
  (let [init-stream (if (and (->> backtest-config :streams-config (map :name) (some #(= % "default"))) (= incint "inception"))
                      [(if fore?
                         (vec (map #(+ % (get backtest-config :num-data-points)) (-> streams first :stream count range)))
                         (vec (range (get backtest-config :num-data-points))))]
                      [])]
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

(defn fetch-formatted-streams
  ([backtest-config] (fetch-formatted-streams backtest-config false))
  ([backtest-config fore?]
   (let [streams (fetch-streams backtest-config fore?)]
     {:inception-streams (get-incint-streams backtest-config streams "inception" fore?)
      :intention-streams (get-incint-streams backtest-config streams "intention" fore?)})))

(defn get-from-to-times-old
  ([granularity _count] (get-from-to-times-old granularity _count 5000))
  ([granularity _count span]
   (let [from-time (util/get-past-unix-time granularity _count)
         to-time (util/current-time-sec)
         time-span (* span (util/granularity->seconds granularity))]
     (reverse
      (map reverse
           (partition
            2 1
            (loop [val to-time vals []]
              (if (<= val from-time)
                (conj vals from-time)
                (recur (- val time-span) (conj vals
                                               val))))))))))

(defn get-big-stream-old
  ([instrument granularity _count] (get-big-stream-old instrument granularity _count 5000))
  ([instrument granularity _count span]
   (let [from-to-times (get-from-to-times-old granularity _count span)
        ;;  foo (println "from-to-times" from-to-times)
         ]
     (mapv
      :o
      (flatten
       (for [from-to-time from-to-times]
         (let [from-time (first from-to-time)
               to-time (second from-to-time)]
           (instruments/get-instrument-stream {:name instrument :granularity granularity :from from-time :to to-time :includeFirst false}))))))))

(defn get-from-to-times
  ([granularity _count] (get-from-to-times granularity _count 5000))
  ([granularity _count span]
   (let [from-time (util/get-past-unix-time granularity _count)
         to-time (util/current-time-sec)
         time-span (* span (util/granularity->seconds granularity))]
     (partition
      2 1
      (loop [val to-time vals []]
        (if (<= val from-time)
          (conj vals from-time)
          (recur (- val time-span) (conj vals val))))))))

(defn get-big-stream
  ([instrument granularity _count] (get-big-stream instrument granularity _count 1000))
  ([instrument granularity _count span]
   (println "get-big-stream" instrument granularity _count span)
   (let [from-to-times (get-from-to-times granularity (* 2 _count) span)
         foo (println "from-to-times:" from-to-times)]
     (loop [i 0 stream []] ;; TODO: Change this from a loop to a reduce to map over from-to-times instead of terminating on stream length
       (let [from-to-time (-> from-to-times (nth i))
             from-time (second from-to-time)
             to-time (first from-to-time)
             foo (println "from-time:" from-time " to-time:" to-time)
             new-stream-section (instruments/get-instrument-stream
                                 {:name instrument
                                  :granularity granularity
                                  :from from-time
                                  :to to-time
                                  :includeFirst true})
             foo (println new-stream-section)
             new-stream (into new-stream-section stream)]
         (if (or (>= i (-> from-to-times count dec)) (>= (count new-stream) _count))
           (mapv :o new-stream)
           (recur (inc i) new-stream)))))))

(comment
  (time (plot/plot-streams [(plot/zero-stream (get-big-stream "EUR_USD" "H1" 100000))]))

  (time (plot/plot-streams [(plot/zero-stream (get-big-stream-old "EUR_USD" "H1" 100000))]))
  ;; end comment
  )

(comment
  (def backtest-config (config/get-backtest-config-util
                        ["EUR_USD" "both" "AUD_USD" "both" "GBP_USD" "inception" "USD_JPY" "inception"]
                        "long-only" 1 2 3 12000 "M15"))

  (def streams (fetch-formatted-streams backtest-config))

  (def strindy (strindy/make-strindy (backtest-config :strindy-config)))

  (def sieve-stream (strindy/get-sieve-stream strindy (get streams :inception-streams)))

  (def return-stream (strindy/sieve->return sieve-stream (get streams :intention-streams)))

  (def big-stream (get-big-stream "EUR_USD" "H1" 20000))

  (count big-stream))
