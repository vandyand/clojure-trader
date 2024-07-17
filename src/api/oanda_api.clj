(ns api.oanda_api
  (:require [clojure.data.json :as json]
            [clj-http.client :as client]
            [env :as env]
            [api.util :as autil]
            [config :as config])
  (:import [java.time Instant]
           [java.time.format DateTimeFormatter]
           [java.util Date]))

;; autilITY FUNCTIONS 

(defn get-oanda-account-endpoint
  ([end] (get-oanda-account-endpoint (env/get-account-id) end))
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
   (autil/get-oanda-api-data (get-oanda-account-endpoint account-id "summary"))))

(defn get-account-balance
  ([] (get-account-balance (env/get-account-id)))
  ([account-id]
   (-> (get-account-summary account-id) :account :balance Double/parseDouble)))

(defn get-account-nav
  ([] (get-account-nav (env/get-account-id)))
  ([account-id]
   (-> (get-account-summary account-id) :account :NAV Double/parseDouble)))

(comment
  (get-account-nav))

(defn get-account-instruments
  ([] (get-account-instruments (env/get-account-id)))
  ([account-id]
   (-> account-id (get-oanda-account-endpoint "instruments") autil/get-oanda-api-data :instruments)))

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

(defn get-api-candle-data-old
  ([instrument-config] (get-api-candle-data-old (env/get-account-id) instrument-config))
  ([account-id instrument-config]
   (let [endpoint (get-oanda-account-endpoint account-id (str "instruments/" (get instrument-config :name) "/candles"))]
     (autil/get-oanda-api-data endpoint instrument-config))))

(def crypto-cache (atom {}))

(defn get-crypto-api-data
  [endpoint]
  (let [current-time (System/currentTimeMillis)
        cached-data (get @crypto-cache endpoint)
        cache-valid? (and cached-data (< (- current-time (:timestamp cached-data)) 60000))]
    (if cache-valid?
      (:data cached-data)
      (let [response (client/get endpoint {:as :json})
            data (:body response)]
        (swap! crypto-cache assoc endpoint {:data data :timestamp current-time})
        data))))

(def robinhood-cache (atom {}))

(defn get-robinhood-api-data
  [endpoint]
  (let [current-time (System/currentTimeMillis)
        cached-data (get @robinhood-cache endpoint)
        cache-valid? (and cached-data (< (- current-time (:timestamp cached-data)) (* 1000 10)))]
    (if cache-valid?
      (:data cached-data)
      (let [response (client/get endpoint {:as :json})
            data (:body response)]
        (swap! robinhood-cache assoc endpoint {:data data :timestamp current-time})
        data))))

#_(get-robinhood-api-data "http://localhost:4322/portfolio_profile")

(defn get-robinhood-equity []
  (-> "http://localhost:4322/portfolio_profile" get-robinhood-api-data :extended_hours_equity Double/parseDouble))

#_(get-robinhood-equity)

(defn map-oanda-to-binance-granularity [oanda-granularity]
  (case oanda-granularity
    "S5" "1s"
    "M1" "1m"
    "M3" "3m"
    "M5" "5m"
    "M15" "15m"
    "M30" "30m"
    "H1" "1h"
    "H2" "2h"
    "H4" "4h"
    "H6" "6h"
    "H8" "8h"
    "H12" "12h"
    "D" "1d"
    "W" "1w"
    "M" "1M"
    oanda-granularity))

#_(map-oanda-to-binance-granularity "M1")

(defn map-oanda-to-robinhood-granularity [oanda-granularity]
  (case oanda-granularity
    "M5" "5minute"
    "M10" "10minute"
    "H1" "hour"
    "D" "day"
    "W" "week"
    oanda-granularity))

(defn get-gran-spans [granularity]
  (filter #(= (:gran %) granularity) constants/num-rh-grans-per-span-map))

#_(get-gran-spans "5minute")

(defn get-least-greater-span [granularity count]
  (:span (first (filter #(>= (:count %) count) (get-gran-spans granularity)))))

#_(get-least-greater-gran-span "5minute" 1000)

(defn get-robinhood-span [instrument-config]
  (let [granularity (map-oanda-to-robinhood-granularity (get instrument-config :granularity))
        count (get instrument-config :count)
        span (get-least-greater-span granularity count)]
    span))

#_(get-robinhood-span {:name "AAPL" :granularity "H1" :count 1000})

(defn get-api-candle-data
  ([instrument-config] (get-api-candle-data (env/get-account-id) instrument-config))
  ([account-id instrument-config]
   (let [instrument-name (get instrument-config :name)
         granularity (get instrument-config :granularity)
         binance-granularity (map-oanda-to-binance-granularity granularity)
         robinhood-granularity (map-oanda-to-robinhood-granularity granularity)
         endpoint (cond
                    (util/is-crypto? instrument-name) (str "http://localhost:4321/candlestick?symbol=" instrument-name
                                                           "&timeframe=" binance-granularity
                                                           "&limit=" (get instrument-config :count))
                    (util/is-forex? instrument-name) (get-oanda-account-endpoint account-id (str "instruments/" instrument-name "/candles"
                                                                                                 "?granularity=" granularity))
                    (util/is-equity? instrument-name) (str "http://localhost:4322/candlestick?symbol=" instrument-name
                                                           "&timeframe=" robinhood-granularity
                                                           "&span=" (get-robinhood-span instrument-config)))]
     (try
       (cond
         (util/is-crypto? instrument-name) (get-crypto-api-data endpoint)
         (util/is-forex? instrument-name) (autil/get-oanda-api-data endpoint)
         (util/is-equity? instrument-name) (get-robinhood-api-data endpoint))
       (catch Exception e
         (println "Error fetching API data:" (.getMessage e))
         (throw e))))))

#_(get-api-candle-data {:name "AAPL" :granularity "M5" :count 100})
#_(get-api-candle-data {:name "AUD_JPY" :granularity "M1" :count 3})
#_(get-api-candle-data {:name "BTCUSDT" :granularity "M1" :count 3})

(comment
  ;; EXPERIMENTAL WORK IN PROGRESS
  (defn get-streaming-price-data
    [instrument]
    (let [endpoint (get-oanda-account-endpoint
                    (env/get-account-id)
                    (str "pricing/stream?instruments=" instrument))]
      (autil/get-oanda-stream-data endpoint)))

  #_(get-streaming-price-data "EUR_USD"))

;; GET OPEN POSITIONS

(defn format-binance-positions [positions]
  (->> positions
       (filter (fn [[_ v]] (not= v 0.0))) ;; Exclude zero positions
       (map (fn [[k v]] {:instrument (name k) :units v}))))

(def binance-cache (atom {:positions nil :timestamp 0}))

(defn get-binance-positions
  ([] (get-binance-positions false))
  ([force-refresh?]
   (let [{:keys [positions timestamp]} @binance-cache
         current-time (System/currentTimeMillis)
         cache-valid? (and positions (< (- current-time timestamp) 180000))]
     (if (and (not force-refresh?) cache-valid?)
       positions
       (let [url "http://localhost:4321/balances"
             response (client/get url {:as :json})
             new-positions (format-binance-positions (:body response))]
         (reset! binance-cache {:positions new-positions :timestamp current-time})
         new-positions)))))

#_(get-binance-positions)

(def robinhood-cache (atom {:positions nil :timestamp 0}))

(defn get-robinhood-positions
  ([] (get-robinhood-positions false))
  ([force-refresh?]
   (let [{:keys [positions timestamp]} @robinhood-cache
         current-time (System/currentTimeMillis)
         cache-valid? (and positions (< (- current-time timestamp) (* 1000 180)))]
     (if (and (not force-refresh?) cache-valid?)
       positions
       (let [url "http://localhost:4322/balances"
             response (client/get url {:as :json})
             active-positions (:body response)]
         (reset! robinhood-cache {:positions active-positions :timestamp current-time})
        ;;  (println "current positions: " active-positions)
         active-positions)))))

#_(def rh-positions (get-robinhood-positions true))

(defn get-open-positions
  ([] (get-open-positions (env/get-account-id)))
  ([account-id] (autil/get-oanda-api-data (get-oanda-account-endpoint account-id "openPositions"))))

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
  "order-options can be made by order_types/make-order-options-util function"
  ([order-options] (send-order-request order-options (env/get-account-id)))
  ([order-options account-id]
   (autil/send-api-post-request
    (autil/build-oanda-url (get-oanda-account-endpoint account-id "orders"))
    (make-request-options order-options))))

(defn send-binance-order [symbol type side amount]
  (let [url "http://localhost:4321/order"
        payload {:symbol symbol
                 :type type
                 :side side
                 :amount amount}
        response (client/post url
                              {:body (json/write-str payload)
                               :headers {"Content-Type" "application/json"}
                               :as :json})]
    (:body response)))

(defn fake-post [url payload]
  {:body {:status 200}})

(defn _send-binance-order [symbol type side amount]
  (let [url "http://localhost:4321/order"
        payload {:symbol symbol
                 :type type
                 :side side
                 :amount amount}
        response (fake-post url
                            {:body (json/write-str payload)
                             :headers {"Content-Type" "application/json"}
                             :as :json})]
    (:body response)))

#_(send-binance-order "BTCUSDT" "market" "buy" 0.0001) ;; WARNING: THIS ACTUALLY BUYS 0.0001 BTC
#_(send-binance-order "BTCUSDT" "market" "sell" 0.0001) ;; WARNING: THIS ACTUALLY SELLS 0.0001BTC
#_(send-binance-order "ETHUSDT" "market" "buy" 0.001) ;; WARNING: THIS ACTUALLY BUYS 0.001 ETH

(defn send-robinhood-usd-order [symbol amount]
  (let [url "http://localhost:4322/order"
        payload {:symbol symbol
                 :amount amount}
        response (client/post url
                              {:body (json/write-str payload)
                               :headers {"Content-Type" "application/json"}
                               :as :json})]
    (:body response)))

#_(send-robinhood-usd-order "TSLA" 2.0) ;; WARNING: THIS ACTUALLY BUYS $2.00 worth of TSLA

(defn get-instrument-stream
  ([name granularity _count] (get-instrument-stream {:name name :granularity granularity :count _count}))
  ([instrument-config]
   (let [candle-data (get-api-candle-data instrument-config)
         instrument (:name instrument-config)
         candles (cond
                   (util/is-crypto? instrument)
                   (vec
                    (for [candle candle-data]
                      {:t (get candle :timestamp)
                       :v (get candle :volume)
                       :o (get candle :open)
                       :h (get candle :high)
                       :l (get candle :low)
                       :c (get candle :close)}))
                   (util/is-forex? instrument)
                   (vec
                    (for [candle (get candle-data :candles)]
                      {:t (get candle :time)
                       :v (get candle :volume)
                       :o (Double/parseDouble (get-in candle [:mid :o]))
                       :h (Double/parseDouble (get-in candle [:mid :h]))
                       :l (Double/parseDouble (get-in candle [:mid :l]))
                       :c (Double/parseDouble (get-in candle [:mid :c]))}))
                   (util/is-equity? instrument)
                   (vec
                    (for [candle candle-data]
                      {:t (get candle :begins_at)
                       :v (get candle :volume)
                       :o (Double/parseDouble (get candle :open_price))
                       :h (Double/parseDouble (get candle :high_price))
                       :l (Double/parseDouble (get candle :low_price))
                       :c (Double/parseDouble (get candle :close_price))})))]
     (util/subvec-end candles (:count instrument-config)))))

#_(get-instrument-stream {:name "BTCUSDT" :granularity "H1" :count 7777})
#_(get-instrument-stream {:name "EUR_USD" :granularity "H1" :count 7777})
#_(get-instrument-stream {:name "AAPL" :granularity "H1" :count 333})

(defn get-latest-price
  [instrument]
  (let [inst-config {:name instrument :granularity (if (util/is-equity? instrument) "M5" "M1") :count 1}]
    (-> inst-config get-instrument-stream last :c)))

#_(get-latest-price "BTCUSDT")
#_(get-latest-price "EUR_USD")
#_(get-latest-price "AAPL")

(defn get-latest-prices [instruments]
  (mapv (fn [instrument] {:instrument instrument :price (get-latest-price instrument)}) instruments))

#_(get-latest-prices ["AUD_USD" "ETHUSDT" "TSLA"])

#_(get-binance-positions)

(defn instrument-has-usdt-in-it? [instrument]
  (not (nil? (re-find #"USDT" instrument))))

(defn get-binance-position-values []
  (vec
   (for [position (get-binance-positions)]
     (let [symb (case (:instrument position)
                  "USD" (:instrument position)
                  "USDT" "USDTUSD"
                  (str (:instrument position) "USDT"))
           latest-price (case (:instrument position)
                          "USD" 1.0
                          "USDT" 1.0
                          (get-latest-price symb))
           usd-amount (* latest-price (:units position))]
       (assoc position :latest-price latest-price :usd-amount usd-amount)))))

(defn sum-usd-amounts
  [records]
  (reduce + (map :usd-amount records)))

#_(sum-usd-amounts)

(defn get-binance-account-usd-amount
  []
  (sum-usd-amounts (get-binance-position-values)))

#_(get-binance-account-usd-amount)

(defn get-robinhood-position-values []
  (vec
   (for [position (get-robinhood-positions)]
     (let [latest-price (get-latest-price (:instrument position))
           usd-amount (* latest-price (:units position))]
       (assoc position :latest-price latest-price :usd-amount usd-amount)))))

(defn get-robinhood-account-usd-amount []
  (sum-usd-amounts (get-robinhood-position-values)))

#_(get-robinhood-account-usd-amount)

;; OANDA STRINDICATOR STUFF

(defn get-instrument-last-candle [instrument granularity]
  (-> instrument (config/get-instrument-config granularity 1) get-api-candle-data :candles last))

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

;; CLOSE OPEN POSITION FOR INSTRUMENT

(defn close-position
  ([instrument] (close-position (env/get-account-id) instrument))
  ([account-id instrument] (close-position account-id instrument true))
  ([account-id instrument long-pos?]
   (do
     (autil/send-api-put-request
      (autil/build-oanda-url
       (get-oanda-account-endpoint account-id (str "positions/" instrument "/close")))
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
  (autil/get-oanda-api-data  (get-oanda-account-endpoint "openTrades")))

(comment

  (get-account-summary)

  (get-account-balance)

  (get-open-trades))

(comment
  (account-instruments->names (get-account-instruments)))
