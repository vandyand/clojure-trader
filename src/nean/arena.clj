(ns nean.arena
  (:require [api.oanda_api :as oapi]
            [clojure.core.async :as async]
            [config :as config]
            [env :as env]
            [file :as file]
            [nean.ga :as ga]
            [nean.xindy2 :as x2]
            [stats :as stats]
            ;; [uncomplicate.neanderthal.core :refer :all]
            ;; [uncomplicate.neanderthal.native :refer :all]
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
  (let [rindies (get-rindies (:num-generations ga-config)
                             pop-config
                             xindy-config
                             (:back-stream streams-map)
                             (:fore-stream streams-map))
        rifts (mapv :shifts rindies)]
    rifts))

(defn lesser [op1 op2]
  (if (< op1 op2) op1 op2))

(defn generate-wrifts
  ([instruments xindy-config pop-config granularity ga-config num-per]
   (vec
    (for [instrument instruments]
      {:instrument instrument
       :rifts (let [streams-map
                    (x2/get-back-fore-streams
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
          (let [instruments ["AUD_CAD" "AUD_CHF" "AUD_JPY"]
                num-per 1
                granularity "H2"
                xindy-config (config/xindy-config 6 100)
                ga-config (config/xindy-ga-config 20 10000 0.75)
                pop-config (config/xindy-pop-config 3000 0.6)
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
    (save-wrifts+stuff wrifts xindy-config granularity)))

(defn xindies->raw-position [xindies]
  (stats/mean (map #(-> % :last-sieve-val) xindies)))

(defn procure-raw-instrument-positions [wrifts+stuff]
  (for [wrifts (:wrifts wrifts+stuff)]
    {:instrument (:instrument wrifts)
     :raw-position (if (empty? (:rifts wrifts))
                     0.0
                     (let [xindies (x2/shifts->xindies
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

(comment
  (let [chann (async/chan)]
    (util/put-future-times chann (util/get-future-unix-times-sec "H2"))
    (async/go-loop []
      (when-some [val (async/<! chann)]
        (let [file-names (get-dir-file-names)
              file-names-account-ids (partition 2 (interleave file-names (util/get-demo-account-ids (count file-names))))]
          (doseq [file-name-account-id file-names-account-ids]
            (procure-and-post-positions (file/read-file (first file-name-account-id)) (second file-name-account-id))))
        (recur)))))

(defn batch-update
  ([] (batch-update 0))
  ([account-id-offset] (batch-update "data/wrifts" account-id-offset))
  ([dir account-id-offset]
   (let [file-names (get-dir-file-names dir)
         file-account-ids (partition 2 (interleave file-names (util/get-demo-account-ids (count file-names) account-id-offset)))]
     (println file-account-ids)
     (doseq [file-account-id file-account-ids]
       (procure-and-post-positions (file/read-file (first file-account-id)) (second file-account-id))))))

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
                            (x2/shifts->xindies instrument shifts xindy-config granularity)
                            account-id)
                           account-id)))

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
