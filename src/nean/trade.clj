(ns nean.trade
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
            [buddy.core.codecs :refer [bytes->hex]]))

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

(defn post-target-pos-oanda
  ([instrument target-pos] (post-target-pos-oanda instrument target-pos (env/get-account-id)))
  ([instrument target-pos account-id]
   (let [current-pos-data (-> (oa/get-open-positions account-id) :positions (util/find-in :instrument instrument))
         long-pos (when current-pos-data (-> current-pos-data :long :units Integer/parseInt))
         short-pos (when current-pos-data (-> current-pos-data :short :units Integer/parseInt))
         current-pos (if current-pos-data (+ long-pos short-pos) 0)
         units (if current-pos-data (- target-pos current-pos) target-pos)]
     (if (= units 0)
       (println "No position change for " instrument "\nCurrent position: " current-pos "\n")
       (do (oa/send-order-request (ot/make-order-options-util instrument units "MARKET") account-id)
           (println "Position change for " instrument "\nOld position: " current-pos "\nNew position: " (+ current-pos units) "\n"))))))

(defn extract-base-asset [instrument]
  (subs instrument 0 (- (count instrument) 4))) ;; Assuming all pairs end with "USDT"

(defn post-target-pos-binance
  ([instrument target-pos]
   (post-target-pos-binance instrument target-pos (env/get-account-id)))
  ([instrument target-pos account-id]
   (let [base-asset (keyword (extract-base-asset instrument))]
     (println "Extracted base asset:" base-asset)

     (let [positions (oa/get-binance-positions)]
       (println "Fetched Binance positions:" positions)

       (let [current-pos-data (get positions base-asset)]
         (println "Current position data for" base-asset ":" current-pos-data)

         (let [current-pos (if current-pos-data
                             (Double/parseDouble (str current-pos-data))
                             0.0)]
           (println "Current position for" instrument ":" current-pos)

           (let [units (- target-pos current-pos)]
             (println "Calculated units to change for" instrument ":" units)

             (if (= units 0.0)
               (println "No position change for" instrument "\nCurrent position:" current-pos "\n")
               (do
                 (oa/send-binance-order instrument "market"
                                        (if (> units 0) "buy" "sell")
                                        (Math/abs units))
                 (println "Position change for" instrument "\nOld position:" current-pos "\nNew position:" (+ current-pos units) "\n"))))))))))

(defn post-target-pos
  [instrument target-pos]
  (if (util/is-crypto? instrument)
    (post-target-pos-binance instrument target-pos)
    (post-target-pos-oanda instrument target-pos)))

(defn post-target-positions [target-instrument-positions]
  (doseq [target-instrument-position target-instrument-positions]
    (post-target-pos (:instrument target-instrument-position)
                     (:target-position target-instrument-position))))

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

(defn stop-trading
  [account-id]
  (let [stop-chan (:stop-chan (get @trade-env account-id))]
    (async/put! stop-chan true)
    (swap! trade-env dissoc account-id)))

(defn stop-all-trading []
  (let [account-ids (oa/get-account-ids)]
    (for [account-id account-ids]
      (stop-trading account-id))))