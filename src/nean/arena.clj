(ns nean.arena
  (:require [api.oanda_api :as oapi]
            [clojure.core.async :as async]
            [config :as config]
            [env :as env]
            [file :as file]
            [nean.ga :as ga]
            [nean.xindy2 :as x2]
            [stats :as stats]
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

(defn generate-wrifts-old
  ([instruments xindy-config pop-config granularity ga-config num-backtests-per-instrument]
   (vec
    (for [instrument instruments]
      (let [rifts (let [streams-map
                        (x2/get-back-fore-streams
                         instrument granularity
                         (:stream-count ga-config)
                         (:back-pct ga-config)
                         (:max-shift xindy-config))]
                    (vec
                     (apply
                      concat
                      (for [_ (range num-backtests-per-instrument)]
                        (generate-rifts streams-map xindy-config pop-config ga-config)))))]
        {:instrument instrument
         :rifts rifts
         :count (count rifts)})))))

(defn generate-wrifts
  ([instruments xindy-config pop-config granularity ga-config num-backtests-per-instrument]
   (vec
    (for [instrument instruments]
      (let [streams-map (x2/get-back-fore-streams
                         instrument granularity
                         (:stream-count ga-config)
                         (:back-pct ga-config)
                         (:max-shift xindy-config))
            futures (for [_ (range num-backtests-per-instrument)]
                      (future (generate-rifts streams-map xindy-config pop-config ga-config)))
            rifts (vec (doall (mapcat deref futures)))]
        {:instrument instrument
         :rifts rifts
         :count (count rifts)})))))

(comment

  (def backtest-params
    {:instruments ["EUR_USD" "AUD_USD" "USD_JPY"]
     :granularity "M15"
     :num-backtests-per-instrument 30
     :xindy-config {:num-shifts 4
                    :max-shift 100}
     :pop-config {:pop-size 200
                  :num-parents 50
                  :num-children 150}
     :ga-config {:num-generations 3
                 :stream-count 1000
                 :back-pct 0.95}})

(time  (generate-wrifts
   (:instruments backtest-params)
   (:xindy-config backtest-params)
   (:pop-config backtest-params)
   (:granularity backtest-params)
   (:ga-config backtest-params)
   (:num-backtests-per-instrument backtest-params)))


  ;;tnemmoc
  )

;; Saved wrifts file should have everything we need to run them.
(defn save-wrifts+stuff
  ([wrifts xindy-config granularity filename]
   (let [file-content {:xindy-config xindy-config :granularity granularity :wrifts wrifts}]
     (file/write-file filename file-content)
     filename)))

(defn gen-backtest-id []
  (subs (bytes->hex (md5 (str (System/currentTimeMillis) (rand)))) 0 7))

(defn get-backtest-ids []
  (->> (file-seq (clojure.java.io/file "data/wrifts/"))
       (map #(.getName %))
       (filter #(clojure.string/ends-with? % ".edn"))
       (map #(first (clojure.string/split % #"\.")))
       vec))

#_(get-backtest-ids)

(defn generate-and-save-wrifts [instruments xindy-config pop-config granularity ga-config num-backtests-per-instrument]
  (let [backtest-id (gen-backtest-id)
        filename (str "data/wrifts/" backtest-id ".edn")
        _ (file/write-file filename {:xindy-config {} :granularity "" :wrifts []})]
    (future (save-wrifts+stuff
             (generate-wrifts
              instruments
              xindy-config
              pop-config
              granularity
              ga-config
              num-backtests-per-instrument)
             xindy-config
             granularity
             filename))
    backtest-id))

(defn backtest [backtest-params]
  (generate-and-save-wrifts
   (:instruments backtest-params)
   (:xindy-config backtest-params)
   (:pop-config backtest-params)
   (:granularity backtest-params)
   (:ga-config backtest-params)
   (:num-backtests-per-instrument backtest-params)))

(comment

  (def backtest-params
    {:instruments ["EUR_USD" "AUD_USD" "USD_JPY"]
     :granularity "M15"
     :num-backtests-per-instrument 1
     :xindy-config {:num-shifts 8
                    :max-shift 100}
     :pop-config {:pop-size 100
                  :num-parents 50
                  :num-children 50}
     :ga-config {:num-generations 3
                 :stream-count 2000
                 :back-pct 0.9}})

  (backtest backtest-params)


  ;;tnemmoc
  )

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

(defn backtest-id->filename
  [backtest-id]
  (str "data/wrifts/" backtest-id ".edn"))

(defn backtest-filename->granularity
  [filename]
  (let [file-content (file/read-file filename)]
    (:granularity file-content)))

(defn backtest-id->backtest [backtest-id]
  (let [filename (backtest-id->filename backtest-id)]
    (file/read-file filename)))

(defonce trade-env (atom {}))

(defn trade
  ([backtest-id] (trade backtest-id (first (oapi/get-some-account-ids 1))))
  ([backtest-id account-id] (trade backtest-id account-id nil))
  ([backtest-id account-id regularity]
   (println "Starting trade function.")
   (let [trade-chan (async/chan)
         stop-chan (async/chan)
         backtest-filename (backtest-id->filename backtest-id)
         backtest-data (file/read-file backtest-filename)]
     (util/put-future-times trade-chan (util/get-future-unix-times-sec (if regularity regularity (:granularity backtest-data))))
     (async/go-loop []
       (async/alt!
         stop-chan
         ([_]
          (println "Stopping trade function.")
          (async/close! trade-chan)
          (async/close! stop-chan))
         trade-chan
         ([val]
          (when val
            (procure-and-post-positions backtest-data account-id)
            (recur)))))
     (let [trade-chans {account-id {:trade-chan trade-chan :stop-chan stop-chan}}]
       (swap! trade-env conj trade-chans)
       trade-chans))))

(defn stop-trading
  [account-id]
  (let [stop-chan (:stop-chan (get @trade-env account-id))]
    (async/put! stop-chan true)
    (swap! trade-env dissoc account-id)))

#_(stop-trading "101-001-5729740-001")

(defn stop-all-trading []
  (let [account-ids (oapi/get-account-ids)]
    (for [account-id account-ids]
      (stop-trading account-id))))

(comment
  (def trade-chans (trade "M15"))

  (async/put! (:stop-chan trade-chans) true)
  ;;tnemmoc
  )

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
                num-backtests-per-instrument 7
                granularity "M5"
                xindy-config (config/xindy-config 7 777)
                ga-config (config/xindy-ga-config 15 20000 0.75)
                pop-config (config/xindy-pop-config 300 0.5)
                wrifts (generate-wrifts instruments xindy-config pop-config granularity ga-config num-backtests-per-instrument)]
            (save-wrifts+stuff wrifts xindy-config granularity "data/wrifts/")))
        (recur (inc i)))))

  (let [instruments ["AUD_CAD" "AUD_USD" "EUR_USD"]
        num-backtests-per-instrument 3
        granularity "S30"
        xindy-config (config/xindy-config 8 100)
        pop-config (config/xindy-pop-config 400 200)
        ga-config (config/xindy-ga-config 10 1000 0.95)
        wrifts (generate-wrifts instruments xindy-config pop-config granularity ga-config num-backtests-per-instrument)]
    (save-wrifts+stuff wrifts xindy-config granularity))
  ;;end comment
  )

(comment
  (def instruments ["AUD_CAD" "AUD_CHF" "AUD_JPY" "AUD_NZD" "AUD_SGD" "AUD_USD" "CAD_CHF" "CAD_JPY"
                    "CAD_SGD" "CHF_JPY" "CHF_ZAR" "EUR_AUD" "EUR_CAD" "EUR_CHF" "EUR_CZK" "EUR_GBP"
                    "EUR_JPY" "EUR_NZD" "EUR_SEK" "EUR_SGD" "EUR_USD" "EUR_ZAR" "GBP_AUD" "GBP_CAD"
                    "GBP_CHF" "GBP_JPY" "GBP_NZD" "GBP_SGD" "GBP_USD" "GBP_ZAR" "NZD_CAD" "NZD_CHF"
                    "NZD_JPY" "NZD_SGD" "NZD_USD" "SGD_CHF" "SGD_JPY" "USD_CAD" "USD_CHF" "USD_CNH"
                    "USD_CZK" "USD_DKK" "USD_JPY" "USD_SEK" "USD_SGD" "USD_THB" "USD_ZAR" "ZAR_JPY"])

  (oapi/get-some-account-ids 5)

  ;; this randomly updates instrument position sizes
  (doseq [x (repeatedly 1000 #(rand-int 100))]
    (post-target-positions
     [{:instrument (rand-nth instruments) :target-position x}]
     (rand-nth (oapi/get-some-account-ids 5)))))
