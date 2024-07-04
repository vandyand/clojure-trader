(ns nean.arena
  (:require [api.oanda_api :as oa]
            [api.order_types :as ot]
            [clojure.core.async :as async]
            [config :as config]
            [env :as env]
            [file :as file]
            [nean.ga :as ga]
            [nean.xindy :as xindy]
            [stats :as stats]
            [util :as util]
            [buddy.core.hash :refer [md5]]
            [buddy.core.codecs :refer [bytes->hex]]
            [constants :as constants]))

(comment
  "strategy = vector of integers (shifts) representing back-shift distances for backtest scoring algorithm.
   strindy = strategy + indicator
   xindy = xpy strindy (map with keys: :shifts :last-sieve-val :last-rel-sieve-val :rivulet :ga-score)
   xindys are what members of the population are in the genetic algorithm
   rindy = robust xindy (fore performance is 'as good as' back performance and made profit in back and fore)
   rindies = robust xindies
   rifts = robust shifts (just the shifts from rindies)
   wrift = wrapped robust shifts (map with keys: :instrument :rifts)
   Wrifts are used to calculate open position size based on robust backtest strategies")

(defn get-robustness [back-xindy fore-xindy]
  (stats/z-score (-> back-xindy :rivulet seq) (-> fore-xindy :rivulet seq)))

(defn combine-xindy [back-xindy fore-xindy total-xindy]
  {:shifts (:shifts back-xindy)
   :robustness (get-robustness back-xindy fore-xindy)
   :back (dissoc back-xindy :shifts :rivulet)
   :fore (dissoc fore-xindy :shifts :rivulet)
   :total (dissoc total-xindy :shifts :rivulet)})

(defn combine-xindies [back-xindies fore-xindies total-xindies]
  (map combine-xindy back-xindies fore-xindies total-xindies))

(defn get-rindies [num-generations pop-config xindy-config back-stream fore-stream total-stream]
  (let [best-xindies (ga/get-parents (ga/run-generations num-generations pop-config xindy-config back-stream) pop-config)
        fore-xindies (for [xindy best-xindies]
                       (xindy/get-xindy-from-shifts (:shifts xindy) (:max-shift xindy-config) fore-stream))
        total-xindies (for [xindy best-xindies]
                        (xindy/get-xindy-from-shifts (:shifts xindy) (:max-shift xindy-config) total-stream))
        full-xindies (combine-xindies best-xindies fore-xindies total-xindies)
        rindies (filter #(and (> (-> % :back :ga-score) 0) (> (-> % :fore :ga-score) 0) (> (:robustness %) -0.25)) full-xindies)]
    (println "num rindies:" (count rindies))
    rindies))

(defn generate-rindies [streams-map xindy-config pop-config ga-config]
  (let [rindies (get-rindies
                 (:num-generations ga-config)
                 pop-config
                 xindy-config
                 (:back-stream streams-map)
                 (:fore-stream streams-map)
                 (:total-stream streams-map))]
    rindies))

(defn generate-wrifts
  ([backtest-params] (generate-wrifts
                      (:instruments backtest-params)
                      (:xindy-config backtest-params)
                      (:pop-config backtest-params)
                      (:granularity backtest-params)
                      (:ga-config backtest-params)
                      (:num-backtests-per-instrument backtest-params)))
  ([instruments xindy-config pop-config granularity ga-config num-backtests-per-instrument]
   (vec
    (for [instrument instruments]
      (let [_ (println instrument)
            streams-map (xindy/get-back-fore-streams
                         instrument granularity
                         (:stream-count ga-config)
                         (:back-pct ga-config)
                         (:max-shift xindy-config))
            futures (for [_ (range num-backtests-per-instrument)]
                      (future (generate-rindies streams-map xindy-config pop-config ga-config)))
            rindies (vec (doall (mapcat deref futures)))
            _ (println rindies)
            rifts (:rifts rindies)]
        {:instrument instrument
         :rifts (mapv :shifts rindies)
         :rindies rindies
         :count (count rifts)})))))

(comment
  (let [backtest-params
        {:instruments ["EUR_USD"]
         :granularity "H1"
         :num-backtests-per-instrument 30
         :xindy-config {:num-shifts 4
                        :max-shift 100}
         :pop-config {:pop-size 200
                      :num-parents 50
                      :num-children 150}
         :ga-config {:num-generations 3
                     :stream-count 2000
                     :back-pct 0.95}}]
    (time  (generate-wrifts backtest-params)))
  ;;end comment
  )

;; Saved wrifts file should have everything we need to run them.
(defn save-backtest
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

(defn run-and-save-backtest
  ([] (run-and-save-backtest {:instruments ["BTCUSDT"]
                              :granularity "H1"
                              :num-backtests-per-instrument 1
                              :xindy-config {:num-shifts 4
                                             :max-shift 20}
                              :pop-config {:pop-size 20
                                           :num-parents 5
                                           :num-children 15}
                              :ga-config {:num-generations 2
                                          :stream-count 200
                                          :back-pct 0.9}}))
  ([backtest-params] (run-and-save-backtest
                      (:instruments backtest-params)
                      (:xindy-config backtest-params)
                      (:pop-config backtest-params)
                      (:granularity backtest-params)
                      (:ga-config backtest-params)
                      (:num-backtests-per-instrument backtest-params)))
  ([instruments xindy-config pop-config granularity ga-config num-backtests-per-instrument]
   (let [backtest-id (gen-backtest-id)
         filename (str "data/wrifts/" backtest-id ".edn")
         _ (file/write-file filename {:xindy-config {} :granularity "" :wrifts []})
         backtest (generate-wrifts instruments xindy-config pop-config granularity ga-config num-backtests-per-instrument)]
     (save-backtest backtest xindy-config granularity filename)
     backtest-id)))

#_(run-and-save-backtest)

(comment

  (def backtest-params
    {:instruments ["EUR_USD" "BTCUSDT"]
     :granularity "H1"
     :num-backtests-per-instrument 30
     :xindy-config {:num-shifts 4
                    :max-shift 1000}
     :pop-config {:pop-size 200
                  :num-parents 50
                  :num-children 150}
     :ga-config {:num-generations 3
                 :stream-count 3000
                 :back-pct 0.95}})

  (run-and-save-backtest backtest-params)

  ;; end comment
  )

(defn xindies->raw-position [xindies]
  (stats/mean (map #(-> % :last-sieve-val) xindies)))

(defn procure-raw-instrument-positions [backtest]
  (for [wrifts (:wrifts backtest)]
    {:instrument (:instrument wrifts)
     :raw-position (if (empty? (:rifts wrifts))
                     0.0
                     (let [xindies (xindy/shifts->xindies
                                    (:instrument wrifts)
                                    (:rifts wrifts)
                                    (:xindy-config backtest)
                                    (:granularity backtest))]
                       (xindies->raw-position xindies)))}))

(defn raw->target-instrument-position [raw-instrument-position account-nav max-pos]
  (let [target-pos (int (+ 0.5 (* 0.05 account-nav (:raw-position raw-instrument-position))))]
    (cond
      (> target-pos max-pos) max-pos
      (< target-pos (* -1 max-pos)) (* -1 max-pos)
      :else target-pos)))

(defn raw->target-instrument-positions [raw-instrument-positions account-id]
  (let [account-nav (oa/get-account-nav account-id)
        max-pos (int (* 1.0 account-nav))]
    (for [raw-instrument-position raw-instrument-positions]
      (assoc raw-instrument-position
             :target-position
             (raw->target-instrument-position raw-instrument-position account-nav max-pos)))))

(defn backtest->target-instruments-positions
  ([backtest] (backtest->target-instruments-positions backtest (env/get-account-id)))
  ([backtest account-id]
   (raw->target-instrument-positions (procure-raw-instrument-positions backtest) account-id)))

#_(-> "75148d6" backtest-id->backtest procure-raw-instrument-positions)

(defn post-target-pos-oanda
  ([instrument target-pos] (post-target-pos-oanda instrument target-pos (env/get-account-id)))
  ([instrument target-pos account-id]
   (let [current-pos-data (-> (oa/get-open-positions account-id) :positions (util/find-in :instrument instrument))
         long-pos (when current-pos-data (-> current-pos-data :long :units Integer/parseInt))
         short-pos (when current-pos-data (-> current-pos-data :short :units Integer/parseInt))
         current-pos (if current-pos-data (+ long-pos short-pos) 0)
         units (int (if current-pos-data (- target-pos current-pos) target-pos))]
     (if (= units 0)
       (println "No position change for " instrument "\nCurrent position: " current-pos "\n")
       (do (oa/send-order-request (ot/make-order-options-util instrument units "MARKET") account-id)
           (println "Position change for " instrument "\nOld position: " current-pos "\nNew position: " (+ current-pos units) "\n"))))))

(defn extract-base-asset [instrument]
  (subs instrument 0 (- (count instrument) 4))) ;; Assuming all pairs end with "USDT"

#_(-> "BTCUSDT" extract-base-asset)

(defn post-target-pos-binance
  ([instrument target-pos]
   (post-target-pos-binance instrument target-pos (env/get-account-id)))
  ([instrument target-pos account-id]
   (let [positions (oa/get-binance-positions)
         _ (println "positions" positions)
         base-asset (extract-base-asset instrument)
         _ (println "base-asset" base-asset)
         current-pos-data (first (filter (fn [pos] (= (:instrument pos) base-asset)) positions))
         _ (println "current-pos-data" current-pos-data)
         current-pos (if current-pos-data (:units current-pos-data) 0.0)
         units (- target-pos current-pos)]
     (println "Calculated units to change for" instrument ":" units)
     (if (= units 0.0)
       (println "No position change for" instrument "\nCurrent position:" current-pos "\n")
       (do
         (oa/send-binance-order instrument "market"
                                (if (> units 0) "buy" "sell")
                                (Math/abs units))
         (println "Position change for" instrument "\nOld position:" current-pos "\nNew position:" (+ current-pos units) "\n"))))))

#_(oa/send-binance-order "BTCUSDT" "market" "buy" 0.0001) ;; WARNING: THIS ACTUALLY BUYS BTC
#_(oa/send-binance-order "BTCUSDT" "market" "sell" 0.0001) ;; WARNING: THIS ACTUALLY SELLS BTC
#_(oa/send-binance-order "ETHUSDT" "market" "buy" 0.001) ;; WARNING: THIS ACTUALLY BUYS ETH

(defn post-target-pos
  [instrument target-pos]
  (if (util/is-crypto? instrument)
    (post-target-pos-binance instrument target-pos)
    (post-target-pos-oanda instrument target-pos)))

(defn post-target-positions [target-instrument-positions]
  (doseq [target-instrument-position target-instrument-positions]
    (post-target-pos (:instrument target-instrument-position)
                     (:target-position target-instrument-position))))

#_(post-target-pos-binance "BTCUSDT" 0.0003)
#_(post-target-pos-binance "ETHUSDT" 0.005)

#_(post-target-pos "ARBUSDT" 3)
#_(post-target-pos "ETHUSDT" 0.004)
#_(post-target-pos "EUR_USD" 10)

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

(defn procure-and-post-positions
  ([backtest-id]
   (let [backtest (backtest-id->backtest backtest-id)
         target-instrument-positions (backtest->target-instruments-positions backtest)]
     (post-target-positions target-instrument-positions))))

(defn run-and-save-backtest-and-procure-positions-sm []
  (let [backtest-params {:instruments ["EUR_USD"]
                         :granularity "H1"
                         :num-backtests-per-instrument 1
                         :xindy-config {:num-shifts 4
                                        :max-shift 20}
                         :pop-config {:pop-size 20
                                      :num-parents 5
                                      :num-children 15}
                         :ga-config {:num-generations 2
                                     :stream-count 200
                                     :back-pct 0.9}}
        backtest-id (run-and-save-backtest backtest-params)
        _ (println "backtest-id: " backtest-id)]
    (procure-and-post-positions backtest-id)))

#_(run-and-save-backtest-and-procure-positions-sm)

(defn run-and-save-backtest-and-procure-positions []
  (doseq [instrument constants/pairs-by-liquidity]
    (let [backtest-params {:instruments [instrument]
                           :granularity "H1"
                           :num-backtests-per-instrument 7
                           :xindy-config {:num-shifts 14
                                          :max-shift 77}
                           :pop-config {:pop-size 77
                                        :num-parents 33
                                        :num-children 44}
                           :ga-config {:num-generations 7
                                       :stream-count 777
                                       :back-pct 0.95}}
          backtest-id (run-and-save-backtest backtest-params)
          _ (println "backtest-id: " backtest-id)]
      (procure-and-post-positions backtest-id))))

#_(run-and-save-backtest-and-procure-positions)

(defonce trade-env (atom {}))

(defn trade
  ([backtest-id] (trade backtest-id nil))
  ([backtest-id regularity]
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
            (procure-and-post-positions backtest-id)
            (recur)))))
     (let [trade-chans {:trade-chan trade-chan :stop-chan stop-chan}]
       (swap! trade-env conj trade-chans)
       trade-chans))))

(comment
  (let [backtest-params
        {:instruments ["EUR_USD"]
         :granularity "M1"
         :num-backtests-per-instrument 30
         :xindy-config {:num-shifts 4
                        :max-shift 1000}
         :pop-config {:pop-size 200
                      :num-parents 50
                      :num-children 150}
         :ga-config {:num-generations 3
                     :stream-count 3000
                     :back-pct 0.95}}
        backtest-id (run-and-save-backtest backtest-params)
        _ (println "backtest-id: " backtest-id)]
    (trade backtest-id (second (oa/get-some-account-ids 2)))))

(defn stop-trading
  [account-id]
  (let [stop-chan (:stop-chan (get @trade-env account-id))]
    (async/put! stop-chan true)
    (swap! trade-env dissoc account-id)))

#_(stop-trading "101-001-5729740-002")

(defn stop-all-trading []
  (let [account-ids (oa/get-account-ids)]
    (for [account-id account-ids]
      (stop-trading account-id))))

#_(stop-all-trading)

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
            (save-backtest wrifts xindy-config granularity "data/wrifts/")))
        (recur (inc i)))))

  ;;end comment
  )

(comment
  (def instruments ["AUD_CAD" "AUD_CHF" "AUD_JPY" "AUD_NZD" "AUD_SGD" "AUD_USD" "CAD_CHF" "CAD_JPY"
                    "CAD_SGD" "CHF_JPY" "CHF_ZAR" "EUR_AUD" "EUR_CAD" "EUR_CHF" "EUR_CZK" "EUR_GBP"
                    "EUR_JPY" "EUR_NZD" "EUR_SEK" "EUR_SGD" "EUR_USD" "EUR_ZAR" "GBP_AUD" "GBP_CAD"
                    "GBP_CHF" "GBP_JPY" "GBP_NZD" "GBP_SGD" "GBP_USD" "GBP_ZAR" "NZD_CAD" "NZD_CHF"
                    "NZD_JPY" "NZD_SGD" "NZD_USD" "SGD_CHF" "SGD_JPY" "USD_CAD" "USD_CHF" "USD_CNH"
                    "USD_CZK" "USD_DKK" "USD_JPY" "USD_SEK" "USD_SGD" "USD_THB" "USD_ZAR" "ZAR_JPY"])

  (oa/get-some-account-ids 5)

  ;; this randomly updates instrument position sizes
  (doseq [x (repeatedly 1000 #(rand-int 100))]
    (post-target-positions
     [{:instrument (rand-nth instruments) :target-position x}]
     (rand-nth (oa/get-some-account-ids 5)))))


