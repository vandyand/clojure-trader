(ns api.util
  (:require
   [clj-http.client :as client]
   [env :as env]
   [clojure.data.json :as json]
   [api.headers :as headers]))

;; API DATA CONFIG

(def granularities {:oanda ["S5" "S10" "S15" "S30" "M1" "M2" "M4" "M5" "M10" "M15" "M30"
                            "H1" "H2" "H3" "H4" "H6" "H8" "H12" "D" "W" "M"]
                    :binance ["1m" "3m" "5m" "15m" "30m" "1h" "2h" "4h" "6h" "8h" "12h" "1d" "3d" "1w" "1M"]
                    :ours ["M1" "M5" "M15" "M30" "H1" "H2" "H4" "H6" "H8" "H12" "D" "W" "M"]})

(defn gran->binance-gran [granularity]
  (case granularity
    "M1" "1m" "M5" "5m" "M15" "15m" "M30" "30m"
    "H1" "1h" "H2" "2h" "H4" "4h" "H6" "6h" "H8" "8h"
    "H12" "12h" "D" "1d" "W" "1w" "M" "1M" granularity))

(defn binancify-candles-instrument-config [instrument-config]
  {:symbol (:name instrument-config) 
   :interval (gran->binance-gran (:granularity instrument-config)) 
   :limit (if (> (:count instrument-config) 1000) 1000 (:count instrument-config))})

;; CONFIG FUNCTIONS 

(defn get-instrument-config 
  ([name granularity] (get-instrument-config name granularity 5000))
  ([name granularity count]
  {:name name :granularity granularity :count count}))

(defn get-instruments-config [config]
  (for [stream-config (filterv #(not= (get % :name) "default") (get config :streams-config))]
      (get-instrument-config (get stream-config :name) (get config :granularity) (get config :num-data-points))))

;; SEND GET PUT POST REQUESTS

(defn send-api-get-request
  ([url headers]
  ;;  (println url headers)
   (client/get url {:headers headers :content-type :json})))

(defn send-api-put-request [url options]
  (client/put url options))

(defn send-api-post-request [url options]
  ;; (client/post url (assoc options :debug true))
  (client/post url options))

;; (defn send-api-post-request [url options]
;;   (println url)
;;   (println options)
;;   (client/post
;;    url
;;    (assoc
;;     {}
;;     :headers {"X-MBX-APIKEY" (get options :X-MBX-APIKEY)}
;;     :content-type "application/x-www-form-urlencoded"
;;     :debug true
;;     :async true)
;;    (fn [response] (println "response is:" response))
;;    (fn [exception] (println "exception is: " (clojure.pprint/pprint exception)))))


;; UTILITY FUNCTIONS

(defn format-query-params [query-params]
   (reduce
    #(str %1 "&" %2)
    (for [kv query-params]
      (str (name (key kv)) "=" (val kv)))))

(defn build-url [target endpoint instrument-config]
  (let [url-keywd (cond (= target "oanda") :OANDA_API_URL
                        (= target "binance") :BINANCE_API_URL)]
    (str (env/get-env-data url-keywd)
         endpoint
         (when instrument-config (str "?" (format-query-params (dissoc instrument-config :name)))))))

(defn build-oanda-url
  ([endpoint] (build-oanda-url endpoint nil))
  ([endpoint instrument-config]
   (build-url "oanda" endpoint instrument-config)))

(defn build-binance-url
  ([endpoint] (build-oanda-url endpoint nil))
  ([endpoint instrument-config]
   (build-url "binance" endpoint instrument-config)))

(defn parse-response-body [response]
  (json/read-str (response :body) :key-fn keyword))

(defn get-api-data [url headers]
  (-> url (send-api-get-request headers) parse-response-body))

(defn get-oanda-api-data
  ([endpoint] (get-oanda-api-data endpoint nil))
  ([endpoint instrument-config]
   (-> endpoint
       (build-oanda-url instrument-config)
       (get-api-data (headers/get-oanda-headers)))))

(defn get-binance-api-data
  ([endpoint] (get-binance-api-data endpoint nil))
  ([endpoint instrument-config]
   (-> endpoint
       (build-binance-url (binancify-candles-instrument-config instrument-config))
       (get-api-data (headers/get-binance-headers)))))


