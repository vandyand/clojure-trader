(ns v0_2_X.streams
  (:require
   [file :as file]
   [util :as util]
   [config :as config]
   [v0_2_X.strindicator :as strindy]
   [api.util :as api_util]
   [api.instruments :as instruments]))

(defn get-instrument-file-name [instrument-config]
  (str "streams/" (get instrument-config :name) "-" (get instrument-config :granularity) ".edn"))

(defn in-time-window? [time-stamp granularity]
  (< (util/current-time-sec) (+ time-stamp (util/granularity->seconds granularity))))

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

;; (defn update-stream-file
;;   ([instrument-config old-stream]
;;    (let [file-name (get-instrument-file-name instrument-config)
;;          new-stream (ostrindy/get-instrument-stream (assoc instrument-config :count 5000))
;;          overlap-ind (util/get-overlap-ind old-stream new-stream)
;;          updated-stream (into old-stream (util/subvec-end new-stream overlap-ind))]
;;      (file/write-file
;;       (str file/data-folder file-name)
;;       {:time-stamp (util/current-time-sec)
;;        :stream updated-stream})
;;      updated-stream)))


(defn get-whole-stream
  [instrument-config]
  (let [file-name (get-instrument-file-name instrument-config)
        file-exists (.exists (clojure.java.io/file (str file/data-folder file-name)))]
    (if (not file-exists)
       (create-stream-file file-name instrument-config)
      (let [file-content (when file-exists (first (file/read-file file-name)))
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

;; (defn get-whole-stream-from-file-or-api
;;   [instrument-config]
;;   (let [file-name (get-instrument-file-name instrument-config)
;;         file-exists (.exists (clojure.java.io/file (str file/data-folder file-name)))
;;         file-content (when file-exists (first (file/read-file file-name)))
;;         file-up-to-date? (when file-content (up-to-date? (get file-content :time-stamp) (get instrument-config :granularity)))]
;;     (if file-up-to-date?
;;       (vec (get file-content :stream))
;;       (vec (update-stream-file instrument-config)))
;;     (let [api-stream (ostrindy/get-instrument-stream (assoc instrument-config :count 5000))]
;;       (file/write-file
;;        (str file/data-folder file-name)
;;        {:time-stamp (util/current-time-sec)
;;         :stream api-stream})
;;       api-stream)))

(defn fetch-streams
  ([backtest-config] (fetch-streams backtest-config false))
  ([backtest-config fore?]
   (let [instruments-config (api_util/get-instruments-config backtest-config)
        ;;  baz (clojure.pprint/pprint backtest-config)
        ;;  bas (clojure.pprint/pprint instruments-config)
         num-data-points (if (and fore? (get backtest-config :stream-proxy))
                             (util/get-fore-ind (get backtest-config :stream-proxy)
                                              (get-whole-stream (first instruments-config)))
                           (get backtest-config :num-data-points))
         shift-data-points (if fore? 0 (-> backtest-config :shift-data-points))
        ;;  foo (println "num-data-points: " num-data-points)
         ]
     (for [instrument-config instruments-config]
       (let [whole-stream (get-whole-stream instrument-config)
             whole-stream-count (count whole-stream)
            ;;  foo (println whole-stream-count num-data-points shift-data-points)
            ;;  stream (util/subvec-end whole-stream num-data-points)
             stream (subvec whole-stream (- whole-stream-count num-data-points shift-data-points) (- whole-stream-count shift-data-points))]
         {:instrument (get instrument-config :name)
          :stream stream})))))

(defn get-incint-streams [backtest-config streams incint fore?]
  (let [init-stream (if (= incint "inception")
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

(comment
  (def backtest-config (config/get-backtest-config-util
                        ["EUR_USD" "both" "AUD_USD" "both" "GBP_USD" "inception" "USD_JPY" "inception"]
                        ;; ["EUR_USD" "intention"]
                        "binary" 1 2 3 100 "M15"))

  (def streams (fetch-formatted-streams backtest-config))

  (def strindy (strindy/make-strindy (backtest-config :strindy-config)))

  (def sieve-stream (strindy/get-sieve-stream strindy (get streams :inception-streams)))

  (def return-stream (strindy/sieve->return sieve-stream (get streams :intention-streams))))
