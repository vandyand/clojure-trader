(ns nean.arena
  (:require [api.oanda_api :as oapi]
            [clojure.core.async :as async]
            [config :as config]
            [env :as env]
            [file :as file]
            [nean.ga :as ga]
            [nean.xindy2 :as x2]
            [stats :as stats]
            [uncomplicate.neanderthal.core :refer :all]
            [uncomplicate.neanderthal.native :refer :all]
            [util :as util]
            [v0_2_X.streams :as streams]
            [v0_3_X.arena :as arena]
            [buddy.core.hash :refer [md5]]
            [buddy.core.codecs :refer [bytes->hex]]))

(comment
  "strindy = strategy + indicator(s)
   xindy = xpy strindy (map with keys: :shifts :sieve :rivulet :score)
   rindy = robust xindy (fore performance is 'as good as' back performance and made profit in back and fore)
   rindies = robust xindies
   rifts = robust shifts (just the shifts from rindies)
   wrift = wrapped robust shifts (map with keys: :instrument :rifts)")

(defn get-robustness [back-xindy fore-xindy]
  (stats/z-score (-> back-xindy :rivulet seq) (-> fore-xindy :rivulet seq)))

(defn combine-xindy [back-xindy fore-xindy]
  {:shifts (:shifts back-xindy)
   :robustness (get-robustness back-xindy fore-xindy)
   :back (dissoc back-xindy :shifts :rivulet)
   :fore (dissoc fore-xindy :shifts :rivulet)})

(defn combine-xindies [back-xindies fore-xindies]
  (map combine-xindy back-xindies fore-xindies))

(defn get-rindies [num-generations pop-config xindy-config back-stream fore-stream]
  (let [best-xindies (ga/get-parents (ga/run-generations num-generations pop-config xindy-config back-stream) pop-config)
        fore-xindies (for [xindy best-xindies]
                       (x2/get-xindy-from-shifts (:shifts xindy) (:max-shift xindy-config) fore-stream))
        full-xindies (combine-xindies best-xindies fore-xindies)
        rindies (filter #(and (> (-> % :back :score) 0) (> (-> % :fore :score) 0) (> (:robustness %) -0.25)) full-xindies)]
    (println "num rindies:" (count rindies))
    rindies))

(defn generate-rifts [streams-map xindy-config pop-config ga-config]
  (let [rindies (get-rindies (:num-generations ga-config) pop-config xindy-config (:back-stream streams-map)
                             (:fore-stream streams-map))
        rifts (mapv :shifts rindies)]
    rifts))

(defn lesser [op1 op2]
  (if (< op1 op2) op1 op2))

(defn get-back-fore-streams [instrument granularity stream-count back-pct max-shift]
  (println "getting: " instrument)
  (let [big-stream (dv (streams/get-big-stream instrument granularity stream-count (lesser 1000 stream-count)))
        back-len (int (* (dim big-stream) back-pct))
        fore-len (- (dim big-stream) back-len)
        back-stream (subvector big-stream 0 back-len)
        fore-stream (subvector
                     big-stream
                     (- back-len max-shift)
                     (+ fore-len max-shift))]
    {:back-stream back-stream :fore-stream fore-stream}))

(defn generate-wrifts
  ([instruments xindy-config pop-config granularity ga-config num-per]
   (vec
    (for [instrument instruments]
      {:instrument instrument
       :rifts (let [streams-map
                    (get-back-fore-streams
                     instrument granularity
                     (:stream-count ga-config)
                     (:back-pct ga-config)
                     (:max-shift xindy-config))]
                (vec
                 (apply
                  concat
                  (for [_ (range num-per)]
                    (generate-rifts streams-map xindy-config pop-config ga-config)))))}))))

;; Saved wrifts file should have everything we need to run them.
(defn save-wrifts+stuff
  ([wrifts xindy-config granularity] (save-wrifts+stuff wrifts xindy-config granularity "data/wrifts/"))
  ([wrifts xindy-config granularity directory]
   (let [file-content {:xindy-config xindy-config :granularity granularity :wrifts wrifts}
         file-name (str directory (-> (md5 (str file-content)) (bytes->hex) (subs 0 6)) ".edn")]
     (file/write-file file-name file-content)
     file-name)))

(defn generate-and-save-wrifts [instruments xindy-config pop-config granularity ga-config num-per]
  (let [wrifts (generate-wrifts instruments xindy-config pop-config granularity ga-config num-per)
        file-name (save-wrifts+stuff wrifts xindy-config granularity)]
    file-name))

(comment
  ;; -----------------------------------------------------------------------------------------------------------------------------
  (async/go-loop [i 0]
    (if (>= i 1)
      "done"
      (do
        (async/go
          (let [instruments ["AUD_CAD" "AUD_CHF" "AUD_JPY" "AUD_NZD" "AUD_SGD" "AUD_USD" "CAD_CHF" "CAD_JPY"
                             "CAD_SGD" "CHF_JPY" "CHF_ZAR" "EUR_AUD" "EUR_CAD" "EUR_CHF" "EUR_CZK" "EUR_GBP"
                             "EUR_JPY" "EUR_NZD" "EUR_SEK" "EUR_SGD" "EUR_USD" "EUR_ZAR" "GBP_AUD" "GBP_CAD"
                             "GBP_CHF" "GBP_JPY" "GBP_NZD" "GBP_SGD" "GBP_USD" "GBP_ZAR" "NZD_CAD" "NZD_CHF"
                             "NZD_JPY" "NZD_SGD" "NZD_USD" "SGD_CHF" "SGD_JPY" "USD_CAD" "USD_CHF" "USD_CNH"
                             "USD_CZK" "USD_DKK" "USD_JPY" "USD_SEK" "USD_SGD" "USD_THB" "USD_ZAR" "ZAR_JPY"]
                num-per 7
                granularity "H2"
                xindy-config (config/xindy-config 6 100)
                ga-config (config/xindy-ga-config 35 20000 0.75)
                pop-config (config/xindy-pop-config 300 0.5)
                wrifts (generate-wrifts instruments xindy-config pop-config granularity ga-config num-per)]
            (save-wrifts+stuff wrifts xindy-config granularity "data/wrifts/")))
        (recur (inc i)))))

  (let [instruments ["AUD_CAD" "AUD_USD"]
        num-per 3
        granularity "S15"
        xindy-config (config/xindy-config 8 100)
        pop-config (config/xindy-pop-config 400 200)
        ga-config (config/xindy-ga-config 10 1000 0.95)
        wrifts (generate-wrifts instruments xindy-config pop-config granularity ga-config num-per)]
    (save-wrifts+stuff wrifts xindy-config granularity))

  ;; end comment
  )

(defn num-weekend-bars [granularity]
  (let [secs-per-bar (util/granularity->seconds granularity)
        secs-per-weekend (* 60 60 24 2)]
    (int (/ secs-per-weekend secs-per-bar))))

(defn shifts->xindies
  "shifts is a vector of shift-vectors. each shift-vector has :num-shifts shifts (ints)"
  [instrument shifts xindy-config granularity]
  (let [new-stream (dv (streams/get-big-stream
                        instrument
                        granularity (+ 2 (num-weekend-bars granularity) (:max-shift xindy-config))))]
    (for [shift-vec shifts]
      (x2/get-xindy-from-shifts shift-vec (:max-shift xindy-config) new-stream))))

(defn xindies->raw-position [xindies]
  (stats/mean (map #(-> % :last-sieve-val) xindies)))

(defn procure-raw-instrument-positions [wrifts+stuff]
  (for [wrifts (:wrifts wrifts+stuff)]
    {:instrument (:instrument wrifts)
     :raw-position (if (empty? (:rifts wrifts))
                     0.0
                     (let [xindies (shifts->xindies
                                    (:instrument wrifts)
                                    (:rifts wrifts)
                                    (:xindy-config wrifts+stuff)
                                    (:granularity wrifts+stuff))]
                       (xindies->raw-position xindies)))}))

(defn raw->target-instrument-position [raw-instrument-position account-nav max-pos]
  (let [target-pos (int (+ 0.5 (* 0.125 account-nav (:raw-position raw-instrument-position))))]
    (cond
      (> target-pos max-pos) max-pos
      (< target-pos (* -1 max-pos)) (* -1 max-pos)
      :else target-pos)))

(defn raw->target-instrument-positions [raw-instrument-positions account-id]
  (let [account-nav (oapi/get-account-nav account-id)
        max-pos (int (* 1.0 account-nav))]
    (for [raw-instrument-position raw-instrument-positions]
      (assoc raw-instrument-position
             :target-position
             (raw->target-instrument-position raw-instrument-position account-nav max-pos)))))

(defn procure-target-instrument-positions [wrifts+stuff account-id]
  (let [raw-instrument-positions (procure-raw-instrument-positions wrifts+stuff)]
    (raw->target-instrument-positions raw-instrument-positions account-id)))

(defn post-target-positions [target-instrument-positions account-id]
  (doseq [target-instrument-position target-instrument-positions]
    (arena/post-target-pos (:instrument target-instrument-position)
                           (:target-position target-instrument-position)
                           account-id)))
(comment
  (def instruments ["AUD_CAD" "AUD_CHF" "AUD_JPY" "AUD_NZD" "AUD_SGD" "AUD_USD" "CAD_CHF" "CAD_JPY"
                    "CAD_SGD" "CHF_JPY" "CHF_ZAR" "EUR_AUD" "EUR_CAD" "EUR_CHF" "EUR_CZK" "EUR_GBP"
                    "EUR_JPY" "EUR_NZD" "EUR_SEK" "EUR_SGD" "EUR_USD" "EUR_ZAR" "GBP_AUD" "GBP_CAD"
                    "GBP_CHF" "GBP_JPY" "GBP_NZD" "GBP_SGD" "GBP_USD" "GBP_ZAR" "NZD_CAD" "NZD_CHF"
                    "NZD_JPY" "NZD_SGD" "NZD_USD" "SGD_CHF" "SGD_JPY" "USD_CAD" "USD_CHF" "USD_CNH"
                    "USD_CZK" "USD_DKK" "USD_JPY" "USD_SEK" "USD_SGD" "USD_THB" "USD_ZAR" "ZAR_JPY"])

  (util/get-demo-account-ids 5 7)

  (doseq [x (repeatedly 1000 #(rand-int 100))]
    (post-target-positions [{:instrument (rand-nth instruments) :target-position x}] (rand-nth (util/get-demo-account-ids 5 7)))))

(defn procure-and-post-positions [wrifts+stuff account-id]
  (let [target-instrument-positions (procure-target-instrument-positions wrifts+stuff account-id)]
    (post-target-positions target-instrument-positions account-id)))

(defn get-dir-file-names
  ([] (get-dir-file-names "data/wrifts"))
  ([dir]
   (map
    (fn [file-name] (str dir "/" file-name))
    (filter
     (fn [file?] (clojure.string/includes? file? ".edn"))
     (seq (.list (clojure.java.io/file (str "./" dir))))))))

(defn batch-update
  ([] (batch-update 0))
  ([account-id-offset] (batch-update "data/wrifts" account-id-offset))
  ([dir account-id-offset]
   (let [file-names (get-dir-file-names dir)
         file-account-ids (partition 2 (interleave file-names (util/get-demo-account-ids (count file-names) account-id-offset)))]
     (println file-account-ids)
     (doseq [file-account-id file-account-ids]
       (procure-and-post-positions (file/read-file (first file-account-id)) (second file-account-id))))))

(comment
  (batch-update)
  (batch-update "data/wrifts/H1"))

(defn scheduled-account-update
  ([granularity] (scheduled-account-update "data/wrifts" granularity))
  ([dir granularity]
   (let [schedule-chan (async/chan)
         files-contents (for [file-name (get-dir-file-names dir)] (file/read-file file-name))]
     (util/put-future-times schedule-chan (util/get-future-unix-times-sec granularity))
     (async/go-loop []
       (when-some [val (async/<! schedule-chan)]
         (let [file-contents-account-ids (partition 2 (interleave files-contents (util/get-demo-account-ids (count files-contents))))]
           (for [file-content-account-id file-contents-account-ids]
             (apply procure-and-post-positions file-content-account-id))))
       (when (not (env/get-env-data :KILL_GO_BLOCKS?)) (recur)))
     schedule-chan)))

(comment
  ;;-------------------------------------------------------------------;;-------------------------------------------------------------------;;-------------------------------------------------------------------;;-------------------------------------------------------------------;;-------------------------------------------------------------------
  ;;-------------------------------------------------------------------;;-------------------------------------------------------------------;;-------------------------------------------------------------------;;-------------------------------------------------------------------;;-------------------------------------------------------------------
  ;;-------------------------------------------------------------------;;-------------------------------------------------------------------;;-------------------------------------------------------------------;;-------------------------------------------------------------------;;-------------------------------------------------------------------
  ;;-------------------------------------------------------------------;;-------------------------------------------------------------------;;-------------------------------------------------------------------;;-------------------------------------------------------------------;;-------------------------------------------------------------------

  ;;-------------------------------------------------------------------;;-------------------------------------------------------------------;;-------------------------------------------------------------------;;-------------------------------------------------------------------;;-------------------------------------------------------------------
  ;;-------------------------------------------------------------------;;-------------------------------------------------------------------;;-------------------------------------------------------------------;;-------------------------------------------------------------------;;-------------------------------------------------------------------
  ;;-------------------------------------------------------------------;;-------------------------------------------------------------------;;-------------------------------------------------------------------;;-------------------------------------------------------------------;;-------------------------------------------------------------------
  ;;-------------------------------------------------------------------;;-------------------------------------------------------------------;;-------------------------------------------------------------------;;-------------------------------------------------------------------;;-------------------------------------------------------------------

  ;;-------------------------------------------------------------------;;-------------------------------------------------------------------;;-------------------------------------------------------------------;;-------------------------------------------------------------------;;-------------------------------------------------------------------
  ;;-------------------------------------------------------------------;;-------------------------------------------------------------------;;-------------------------------------------------------------------;;-------------------------------------------------------------------;;-------------------------------------------------------------------
  ;;-------------------------------------------------------------------;;-------------------------------------------------------------------;;-------------------------------------------------------------------;;-------------------------------------------------------------------;;-------------------------------------------------------------------
  ;;-------------------------------------------------------------------;;-------------------------------------------------------------------;;-------------------------------------------------------------------;;-------------------------------------------------------------------;;-------------------------------------------------------------------

  ;;-------------------------------------------------------------------;;-------------------------------------------------------------------;;-------------------------------------------------------------------;;-------------------------------------------------------------------;;-------------------------------------------------------------------
  ;;-------------------------------------------------------------------;;-------------------------------------------------------------------;;-------------------------------------------------------------------;;-------------------------------------------------------------------;;-------------------------------------------------------------------
  ;;-------------------------------------------------------------------;;-------------------------------------------------------------------;;-------------------------------------------------------------------;;-------------------------------------------------------------------;;-------------------------------------------------------------------
  ;;-------------------------------------------------------------------;;-------------------------------------------------------------------;;-------------------------------------------------------------------;;-------------------------------------------------------------------;;-------------------------------------------------------------------

  ;; (let [chann (async/chan)]
  ;;   (util/put-future-times chann (util/get-future-unix-times-sec "H1"))
  ;;   (async/go-loop []
  ;;     (when-some [val (async/<! chann)]
  ;;       (batch-update)
  ;;       (recur))))


  (let [chann (async/chan)]
    (util/put-future-times chann (util/get-future-unix-times-sec "H2"))
    (async/go-loop []
      (when-some [val (async/<! chann)]
        (let [file-names (get-dir-file-names)
              file-names-account-ids (partition 2 (interleave file-names (util/get-demo-account-ids (count file-names))))]
          (doseq [file-name-account-id file-names-account-ids]
            (procure-and-post-positions (file/read-file (first file-name-account-id)) (second file-name-account-id))))
        (recur))))


  ;;-------------------------------------------------------------------;;-------------------------------------------------------------------;;-------------------------------------------------------------------;;-------------------------------------------------------------------;;-------------------------------------------------------------------
  ;;-------------------------------------------------------------------;;-------------------------------------------------------------------;;-------------------------------------------------------------------;;-------------------------------------------------------------------;;-------------------------------------------------------------------
  ;;-------------------------------------------------------------------;;-------------------------------------------------------------------;;-------------------------------------------------------------------;;-------------------------------------------------------------------;;-------------------------------------------------------------------
  ;;-------------------------------------------------------------------;;-------------------------------------------------------------------;;-------------------------------------------------------------------;;-------------------------------------------------------------------;;-------------------------------------------------------------------

  ;;-------------------------------------------------------------------;;-------------------------------------------------------------------;;-------------------------------------------------------------------;;-------------------------------------------------------------------;;-------------------------------------------------------------------
  ;;-------------------------------------------------------------------;;-------------------------------------------------------------------;;-------------------------------------------------------------------;;-------------------------------------------------------------------;;-------------------------------------------------------------------
  ;;-------------------------------------------------------------------;;-------------------------------------------------------------------;;-------------------------------------------------------------------;;-------------------------------------------------------------------;;-------------------------------------------------------------------
  ;;-------------------------------------------------------------------;;-------------------------------------------------------------------;;-------------------------------------------------------------------;;-------------------------------------------------------------------;;-------------------------------------------------------------------

  ;;-------------------------------------------------------------------;;-------------------------------------------------------------------;;-------------------------------------------------------------------;;-------------------------------------------------------------------;;-------------------------------------------------------------------
  ;;-------------------------------------------------------------------;;-------------------------------------------------------------------;;-------------------------------------------------------------------;;-------------------------------------------------------------------;;-------------------------------------------------------------------
  ;;-------------------------------------------------------------------;;-------------------------------------------------------------------;;-------------------------------------------------------------------;;-------------------------------------------------------------------;;-------------------------------------------------------------------
  ;;-------------------------------------------------------------------;;-------------------------------------------------------------------;;-------------------------------------------------------------------;;-------------------------------------------------------------------;;-------------------------------------------------------------------

  ;;-------------------------------------------------------------------;;-------------------------------------------------------------------;;-------------------------------------------------------------------;;-------------------------------------------------------------------;;-------------------------------------------------------------------
  ;;-------------------------------------------------------------------;;-------------------------------------------------------------------;;-------------------------------------------------------------------;;-------------------------------------------------------------------;;-------------------------------------------------------------------
  ;;-------------------------------------------------------------------;;-------------------------------------------------------------------;;-------------------------------------------------------------------;;-------------------------------------------------------------------;;-------------------------------------------------------------------
  ;;-------------------------------------------------------------------;;-------------------------------------------------------------------;;-------------------------------------------------------------------;;-------------------------------------------------------------------;;-------------------------------------------------------------------

  ;;
  )

(defn get-position-from-xindieses [xindieses account-id]
  (let [account-balance (oapi/get-account-balance account-id)
        max-pos (int (* 1.0 account-balance))
        target-pos (int
                    (+ 0.5
                       (* 0.125 account-balance
                          (stats/mean
                           (for [xindies xindieses]
                             (stats/mean (map #(-> % :last-sieve-val) xindies)))))))]
    (cond
      (> target-pos max-pos) max-pos
      (< target-pos (* -1 max-pos)) (* -1 max-pos)
      :else target-pos)))

(defn wrifts->posted-positions [instrument shifts xindy-config granularity account-id]
  (async/go
    (arena/post-target-pos instrument
                           (get-position-from-xindieses
                            (shifts->xindies instrument shifts xindy-config granularity)
                            account-id)
                           account-id)))

(comment
  ;; (def cont (file/read-file "data/wrifts/4d3aac7a698c6c743e6c0491d08b7640.edn"))

  (for [file-name (get-dir-file-names)]
    (let [wrifts+stuff (file/read-file (str "data/wrifts/" file-name))]
      (procure-and-post-positions wrifts+stuff))))

(defn scheduled-wrifts-runner
  ([wr xc g] (scheduled-wrifts-runner xc g (env/get-account-id)))
  ([wrifts xindy-config granularity account-id]
   (let [schedule-chan (async/chan)]
     (util/put-future-times schedule-chan (util/get-future-unix-times-sec granularity))
     (async/go-loop []
       (when-some [val (async/<! schedule-chan)]
         (doseq [wrift wrifts]
           (wrifts->posted-positions (:instrument wrift) (:rifts wrift) xindy-config granularity account-id)))
       (when (not (env/get-env-data :KILL_GO_BLOCKS?)) (recur)))
     schedule-chan)))

(defn scheduled-wrifts-runner-from-file [file-name account-id]
  (let [{:keys [wrifts xindy-config granularity]} (file/read-file file-name)]
    (scheduled-wrifts-runner wrifts xindy-config granularity account-id)))

(defn generate-and-run-wrifts
  [instruments granularities account-ids xindy-config pop-config ga-config]
  (doseq [gran-account-id (partition 2 (interleave granularities account-ids))]
    (async/go
      (let [granularity (first gran-account-id)
            account-id (second gran-account-id)
            file-name (generate-and-save-wrifts instruments xindy-config pop-config granularity ga-config)]
        (scheduled-wrifts-runner-from-file file-name account-id)))))

(comment
  (let [account-ids ["101-001-5729740-001"]
        instruments ["EUR_USD" "AUD_USD"]
        granularities ["M1"]
        xindy-config (config/xindy-config 10 100)
        pop-config (config/xindy-pop-config 100 25)
        ga-config (config/xindy-ga-config 2 20000 0.95)]
    (generate-and-run-wrifts instruments granularities account-ids xindy-config pop-config ga-config)))

(comment
  ;; (do
  (def instruments ["EUR_USD" "AUD_USD"])

  (def instruments ["EUR_USD" "USD_JPY" "EUR_GBP" "AUD_USD"
                    "EUR_JPY" "GBP_USD" "USD_CHF" "AUD_JPY"
                    "USD_CAD" "CHF_JPY" "EUR_CHF" "CAD_CHF"
                    "NZD_USD" "EUR_CAD" "AUD_CHF" "CAD_JPY"])

  (def instruments ["AUD_CAD" "AUD_CHF" "AUD_JPY" "AUD_NZD" "AUD_SGD" "AUD_USD" "CAD_CHF" "CAD_JPY"
                    "CAD_SGD" "CHF_JPY" "CHF_ZAR" "EUR_AUD" "EUR_CAD" "EUR_CHF" "EUR_CZK" "EUR_GBP"
                    "EUR_JPY" "EUR_NZD" "EUR_SEK" "EUR_SGD" "EUR_USD" "EUR_ZAR" "GBP_AUD" "GBP_CAD"
                    "GBP_CHF" "GBP_JPY" "GBP_NZD" "GBP_SGD" "GBP_USD" "GBP_ZAR" "NZD_CAD" "NZD_CHF"
                    "NZD_JPY" "NZD_SGD" "NZD_USD" "SGD_CHF" "SGD_JPY" "USD_CAD" "USD_CHF" "USD_CNH"
                    "USD_CZK" "USD_DKK" "USD_JPY" "USD_SEK" "USD_SGD" "USD_THB" "USD_ZAR" "ZAR_JPY"])

  (def instrument-freq 1)
  (def granularity "H1")
  (def xindy-config (config/xindy-config 8 750))
  (def pop-config (config/xindy-pop-config 15 7))
  (def ga-config (config/xindy-ga-config 1 20000 0.95))

  (def file-name (generate-wrifts-vec instruments xindy-config pop-config granularity ga-config instrument-freq))

  (run-wrifts-vec-from-file file-name "101-001-5729740-004")

  (generate-and-run-wrifts-vec
   instruments ["H1" "H1" "H1"]
   ["101-001-5729740-001" "101-001-5729740-002" "101-001-5729740-003"] xindy-config
   pop-config ga-config
   instrument-freq)

  (def contents (file/read-file file-name))

  (let [{:keys [wrifts-vec xindy-config granularity]} (file/read-file file-name)]
    ;; (println (ffirst wrifts-vec) xindy-config granularity)
    (get-position-from-xindieses
     (get-new-xindieses-from-wrifts
      (ffirst wrifts-vec)
      xindy-config
      granularity)
     "101-001-5729740-011"))

  (let [{:keys [wrifts-vec xindy-config granularity]} (file/read-file file-name)]
    ;; (println (first wrifts-vec) xindy-config granularity)
    (for [wrifts (first wrifts-vec)]
      (arena/post-target-pos
       (:instrument wrifts)
       (get-position-from-xindieses
        (get-new-xindieses-from-wrifts
         wrifts
         xindy-config
         granularity)
        "101-001-5729740-011")
       "101-001-5729740-011")))



  ;; end comment
  )

(comment

  (let [granularity "M5"
        account-id "101-001-5729740-001"
        schedule-chan (async/chan)]
    (util/put-future-times schedule-chan (util/get-future-unix-times-sec granularity))
    (async/go-loop []
      (when-some [val (async/<! schedule-chan)]
        (let [instruments ["USD_CHF"]
              xindy-config (config/get-xindy-config 4 250)
              pop-config (ga/xindy-pop-config 50 20)
              ga-config (ga/xindy-ga-config 10 25000 0.95)
              instrument-freq 7
              wrifts-vec (generate-wrifts-vec instruments xindy-config pop-config granularity ga-config instrument-freq)]
          (doseq [wrifts wrifts-vec]
            (async/go
              (arena/post-target-pos
               (:instrument wrifts)
               (get-position-from-xindieses
                (get-new-xindieses-from-wrifts
                 wrifts
                 xindy-config
                 granularity)
                account-id)
               account-id)))))
      (when (not (env/get-env-data :KILL_GO_BLOCKS?)) (recur)))
    schedule-chan)

  ;; End Comment
  )


(comment
  (def xindy-config (config/get-xindy-config 6 500))
  (def pop-config (ga/xindy-pop-config 4000 1000))
  (def ga-config (ga/xindy-ga-config 10 100000 0.95))
  (def instruments ["EUR_USD" "USD_JPY" "EUR_JPY"])
  (def instrument-freq 3)
  (def granularities ["M10" "M30" "H2"])
  (def account-ids ["101-001-5729740-004" "101-001-5729740-005" "101-001-5729740-006"])
  (generate-and-run-wrifts-vec
   instruments granularities
   account-ids xindy-config
   pop-config ga-config
   instrument-freq)


  (def instruments ["EUR_USD" "USD_JPY" "EUR_GBP" "AUD_USD"
                    "EUR_JPY" "GBP_USD" "USD_CHF" "AUD_JPY"
                    "USD_CAD" "CHF_JPY" "EUR_CHF" "CAD_CHF"
                    "NZD_USD" "EUR_CAD" "AUD_CHF" "CAD_JPY"])
  ;; (def granularities ["M4" "M5" "M10" "M15" "M30" "H1" "H2"])
  ;; (def account-ids ["101-001-5729740-001" "101-001-5729740-002" "101-001-5729740-003"
  ;;                   "101-001-5729740-004" "101-001-5729740-005" "101-001-5729740-006"
  ;;                   "101-001-5729740-007"])

  ;; end comment
  )


(comment
  (def all-config (merge {:instruments instruments} xindy-config pop-config {:granularity granularity} ga-config {:instrument-freq instrument-freq}))

  (keys all-config)
  (map str (vals all-config))

  (stats/stdev (streams/get-big-stream "EUR_USD" "M5" 10000))

  ;; End Comment
  )


;; (defn save-wrifts-vec [file-name wrifts-vec all-config]
;;   (file/write-file file-name wrifts-vec))

;; (defn get-and-save-wrifts-vec [file-name & generate-wrifts-vec-args]
;;   (save-wrifts-vec file-name (apply generate-wrifts-vec generate-wrifts-vec-args)))



;; (defn run-wrifts-vec-from-file
;;   ([file-name]
;;    (let [file-content (file/read-collection-file file-name)
;;          {:keys [granularity wrifts-vec xindy-config account-id]} file-content
;;          schedule-chan (async/chan)]
;;      (util/put-future-times schedule-chan (util/get-future-unix-times-sec granularity))
;;      (async/go-loop []
;;        (when-some [val (async/<! schedule-chan)]
;;          (doseq [wrifts wrifts-vec]
;;            (async/go
;;              (arena/post-target-pos
;;               (:instrument wrifts)
;;               (get-position-from-xindieses
;;                (get-new-xindieses-from-wrifts
;;                 wrifts
;;                 xindy-config
;;                 granularity)
;;                account-id)
;;               account-id))))
;;        (when (not (env/get-env-data :KILL_GO_BLOCKS?)) (recur)))
;;      schedule-chan)))
