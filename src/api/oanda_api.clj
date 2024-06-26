(ns api.oanda_api
  (:require [clojure.data.json :as json]
            [env :as env]
            [api.util :as autil]))

;; autilITY FUNCTIONS 

(defn get-account-endpoint
  ([end] (get-account-endpoint (env/get-account-id) end))
  ([account-id end]
   (str "accounts/" account-id "/" end)))

;; ACCOUNT DATA FUNCTIONS

(defn get-accounts []
  (sort-by :id (:accounts (autil/get-oanda-api-data "accounts"))))

(defn get-account-ids []
  (mapv :id (get-accounts)))

(defn get-some-account-ids [_num]
  (let [account-ids (get-account-ids)]
    (subvec account-ids 0 (min _num (count account-ids)))))

#_(get-accounts)
#_(get-account-ids)

(defn get-account-summary
  ([] (get-account-summary (env/get-account-id)))
  ([account-id]
   (autil/get-oanda-api-data (get-account-endpoint account-id "summary"))))

(defn get-account-balance
  ([] (get-account-balance (env/get-account-id)))
  ([account-id]
   (-> (get-account-summary account-id) :account :balance Double/parseDouble)))

(defn get-account-nav
  ([] (get-account-balance (env/get-account-id)))
  ([account-id]
   (-> (get-account-summary account-id) :account :NAV Double/parseDouble)))

(comment
  (get-account-nav))

(defn get-account-instruments
  ([] (get-account-instruments (env/get-account-id)))
  ([account-id]
   (-> account-id (get-account-endpoint "instruments") autil/get-oanda-api-data :instruments)))

(comment

  (get-account-instruments)

  (def account-instruments (get-account-instruments))

  (def decent-margin-rate-instruments (filter #(< (-> % :marginRate Double/parseDouble) 0.1) account-instruments))

  (clojure.pprint/pprint (map :name decent-margin-rate-instruments))
  ;; End Comment
  )

(defn get-account-instrument [instrument]
  (let [instruments (get-account-instruments)]
    (first (filter #(= instrument (% :name)) instruments))))

(defn get-instrument-precision [instrument]
  (-> instrument get-account-instrument :displayPrecision))

(defn account-instruments->names [account-instruments]
  (map (fn [instrument] (:name instrument)) (:instruments account-instruments)))

;; GET CANDLES

(defn get-api-candle-data
  ([instrument-config] (get-api-candle-data (env/get-account-id) instrument-config))
  ([account-id instrument-config]
   (let [endpoint (get-account-endpoint account-id (str "instruments/" (get instrument-config :name) "/candles"))]
     (autil/get-oanda-api-data endpoint instrument-config))))

(comment
  (get-api-candle-data {:name "AUD_JPY" :granularity "M1" :count 3}))

(comment
  ;; EXPERIMENTAL WORK IN PROGRESS
  (defn get-streaming-price-data
    [instrument]
    (let [endpoint (get-account-endpoint
                    (env/get-account-id)
                    (str "pricing/stream?instruments=" instrument))
          _ (println endpoint)]
      (autil/get-oanda-stream-data endpoint)))

  #_(get-streaming-price-data "EUR_USD"))

;; GET OPEN POSITIONS

(defn get-open-positions
  ([] (get-open-positions (env/get-account-id)))
  ([account-id] (autil/get-oanda-api-data (get-account-endpoint account-id "openPositions"))))

#_(get-open-positions)

(defn get-formatted-open-positions
  ([] (get-formatted-open-positions (env/get-account-id)))
  ([account-id]
   (let [cur-poss-data (-> (get-open-positions account-id) :positions)]
     (for [current-position-data cur-poss-data]
       (let [instrument (-> current-position-data :instrument)
             long-pos (-> current-position-data :long :units Integer/parseInt)
             short-pos (-> current-position-data :short :units Integer/parseInt)]
         {:instrument instrument :units (+ long-pos short-pos)})))))

#_(get-formatted-open-positions)

#_(get-formatted-open-positions-by-account)

;; SEND ORDER FUNCTIONS

(defn make-request-options [body]
  {:headers (autil/get-oanda-headers)
   :content-type :json
   :body (json/write-str body)
   :as :json})

(defn send-order-request
  "order-options can be made by order_types/make-order-options-autil function"
  ([order-options] (send-order-request order-options (env/get-account-id)))
  ([order-options account-id]
   (autil/send-api-post-request
    (autil/build-oanda-url (get-account-endpoint account-id "orders"))
    (make-request-options order-options))))

(defn get-instrument-stream [instrument-config]
  (let [api-data (get-api-candle-data instrument-config)]
    (vec
     (for [candle (get api-data :candles)]
       {:v (get candle :volume)
        :o (Double/parseDouble (get-in candle [:mid :o]))
        :h (Double/parseDouble (get-in candle [:mid :h]))
        :l (Double/parseDouble (get-in candle [:mid :l]))
        :c (Double/parseDouble (get-in candle [:mid :c]))}))))

(comment

  (ot/make-order-options-autil "EUR_USD" 50 "GTD" "H1" 0.005 0.005)

  (send-order-request (ot/make-order-options-autil "EUR_USD" 5))

  (send-order-request (ot/make-order-options-autil "EUR_USD" -50 "GTD" "H1" 0.005 0.005)))

;; OANDA STRINDICATOR STUFF

(defn get-instrument-last-candle [instrument granularity]
  (-> instrument (autil/get-instrument-config granularity 1) get-api-candle-data :candles last))

(defn get-current-candle-open-time [granularity]
  (-> "EUR_USD" (get-instrument-last-candle (or granularity "H1")) :time Double/parseDouble))

(defn get-instrument-current-price-by-ohlc
  ([instrument ohlc-key] (get-instrument-current-price-by-ohlc instrument ohlc-key "M1"))
  ([instrument ohlc-key granularity]
   (-> instrument (get-instrument-last-candle granularity) :mid ohlc-key Double/parseDouble)))

(defn get-instrument-current-candle-ohlc [instrument granularity ohlc]
  (get-instrument-current-price-by-ohlc instrument ohlc (or granularity "H1")))

(defn get-formatted-candle-data [instrument-config]
  (let [api-data (get-api-candle-data instrument-config)]
    (vec
     (for [candle (get api-data :candles)]
       {:v (get candle :volume)
        :o (Double/parseDouble (get-in candle [:mid :o]))
        :h (Double/parseDouble (get-in candle [:mid :h]))
        :l (Double/parseDouble (get-in candle [:mid :l]))
        :c (Double/parseDouble (get-in candle [:mid :c]))}))))

(comment
  (get-formatted-candle-data {:name "USD_CNY" :granularity "H1" :count 3000}))


;; GET STREAMING PRICE DATA

(defn open-streaming-price-channel [instrument])

;; CLOSE OPEN POSITION FOR INSTRUMENT

(defn close-position
  ([instrument] (close-position (env/get-account-id) instrument))
  ([account-id instrument] (close-position account-id instrument true))
  ([account-id instrument long-pos?]
   (do
     (autil/send-api-put-request
      (autil/build-oanda-url
       (get-account-endpoint account-id (str "positions/" instrument "/close")))
      (make-request-options (if long-pos? {:longUnits "ALL"} {:shortUnits "ALL"})))
     instrument)))

(defn close-positions
  ([] (close-positions (env/get-account-id)))
  ([account-id]
   (let [positions (get-formatted-open-positions account-id)]
     (for [position positions]
       (close-position account-id (:instrument position) (> (:units position) 0))))))

(defn close-all-positions
  ([] (close-all-positions (get-account-ids)))
  ([account-ids]
   (for [account-id account-ids]
     {:account-id account-id :closed (close-positions account-id)})))

(comment
  (def account-ids ["101-001-5729740-001" "101-001-5729740-002" "101-001-5729740-003"
                    "101-001-5729740-004" "101-001-5729740-005" "101-001-5729740-006"
                    "101-001-5729740-007" "101-001-5729740-008" "101-001-5729740-009"
                    "101-001-5729740-010" "101-001-5729740-011" "101-001-5729740-012"
                    "101-001-5729740-013" "101-001-5729740-014" "101-001-5729740-015"])
  (def account-ids ["101-001-5729740-001" "101-001-5729740-002" "101-001-5729740-003"])

  (close-all-positions account-ids)

  ;; end comment
  )

;; TRADES FUNCTIONS

(defn get-open-trades []
  (autil/get-oanda-api-data  (get-account-endpoint "openTrades")))

(comment

  (get-account-summary)

  (get-account-balance)

  (get-open-trades))

(comment
  (account-instruments->names (get-account-instruments)))
