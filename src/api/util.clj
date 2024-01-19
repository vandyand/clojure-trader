(ns api.util
  (:require
   [clj-http.client :as client]
   [util :as util]
   [env :as env]
   [clojure.data.json :as json]
   [api.headers :as headers]
   [org.httpkit.client :as hk-client]
   [clojure.java.io :as io]
   [clojure.java.shell :refer [sh]]))

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
   (client/get url {:headers headers :content-type :octet-stream})
  ;;  (client/get url {:headers headers :content-type :json :throw-exceptions false})
  ;;  (client/get url {:headers headers :content-type :json :debug true})
   ))

(defn send-api-put-request [url options]
  (client/put url options))

(defn send-api-post-request [url options]
  ;; (client/post url (assoc options :debug false))
  ;; (client/post url options)
  (try (client/post url options)
       (catch Exception e (println "caught exception: " (.getMessage e))))
  )

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
  (let [account-type (env/get-env-data :OANDA_LIVE_OR_DEMO)
        url-keywd (cond (= target "oanda") (if (= account-type "LIVE") :OANDA_LIVE_URL :OANDA_DEMO_URL)
                        (= target "binance") :BINANCE_API_URL)]
    (str (env/get-env-data url-keywd)
         endpoint
         (when instrument-config (str "?" (format-query-params (dissoc instrument-config :name)))))))

(defn build-oanda-stream-url
  [endpoint]
  (let [stream-url (env/get-env-data (if (env/is-live-account?) :OANDA_LIVE_STREAM_URL :OANDA_DEMO_STREAM_URL))]
    (str stream-url endpoint)))

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

(defn get-oanda-stream-data-old
  [endpoint]
(-> endpoint 
    (build-oanda-stream-url)
    (get-api-data (headers/get-oanda-headers))))

(require '[clojure.core.async :as async])

(defn get-oanda-stream-data
  [endpoint]
  (let [response (send-api-get-request 
                  (build-oanda-stream-url endpoint) 
                  (headers/get-oanda-headers))
        _ (println "response:" response)
        ch (async/chan)]
    (async/thread
      (with-open [reader (java.io.BufferedReader. (java.io.InputStreamReader. (:body response)))]
        (doseq [line (line-seq reader)]
          (println )
          (async/>!! ch line))))
    ch))

(comment
  (def endpoint "accounts/101-001-5729740-001/pricing/stream?instruments=EUR_USD")
  (def stream-chan (get-oanda-stream-data endpoint))

  (async/go-loop []
    (when-some [data (async/<! stream-chan)]
      (println data)))

  (send-api-get-request
   (build-oanda-stream-url endpoint)
   (headers/get-oanda-headers))

  (def conn  (let [endpoint "accounts/101-001-5729740-001/pricing/stream?instruments=EUR_USD"
                   _ (println endpoint)
                   url (build-oanda-stream-url endpoint)
                   _ (println url)
                   headers {"Authorization" (str "Bearer " (env/get-oanda-api-key))
                            "Content-Type" "application/json"}
                   _ (println headers)
                   res (hk-client/get url {:headers headers :as :stream})
                   _ (println "res:" @res)]
               res))

  (def endpoint "accounts/101-001-5729740-001/pricing/stream?instruments=EUR_USD%2CUSD_JPY")
  (println endpoint)

  (def url (build-oanda-stream-url endpoint))
  (println url)

  (def headers {"Authorization" (str "Bearer " (env/get-oanda-api-key))})
  (println headers)

  (defn read-stream [input-stream]
    (let [buffer-size 1024  ; Smaller buffer size
          reader (java.io.BufferedReader. (java.io.InputStreamReader. input-stream) buffer-size)]
      (loop []
        (when-let [line (.readLine reader)]
          (println "Received line:" line)
          (recur)))))

  (defn streaming-callback [{:keys [status body error]}]
    (println "Status:" status)
    (if error
      (println "Error:" error)
      (read-stream body)))

  (defn start-streaming []
    (let [res (hk-client/get url {:headers headers :timeout 10000 :as :stream} streaming-callback)
          _ (println "Streaming started, callback will handle the data.")]
      res))
  
;; Call start-streaming to initiate the streaming request
  (def res (start-streaming)) 

  
  
  (let [time (System/currentTimeMillis)]
    (hk-client/get "http://http-kit.org" {:my-start-time time} callback))

  (defn callback [{:keys [status headers body error opts]}]
    ;; opts will include all keys from request call:
    (let [{:keys [method url my-start-time]} opts]
      (println method url "status" status "in"
               (- (System/currentTimeMillis) my-start-time) "ms")))
  ;; tnemmoc
  )

(comment

  (defn read-stream [reader]
    (with-open [rdr reader]
      (doseq [line (line-seq rdr)]
        (println "Received line:" line))))

  (defn start-curl-process []
    (let [process-builder (ProcessBuilder. ["curl" 
                                            "--no-buffer" 
                                            "-H" "Authorization: Bearer 808b8c2978ded93c563bc420348788ab-00fba0cf47cf2456d8b4bfeb4c65c312"
                                            "-H" "Accept-Datetime-Format: UNIX"
                                            "https://stream-fxpractice.oanda.com/v3/accounts/101-001-5729740-001/pricing/stream?instruments=EUR_USD%2CUSD_CAD%2CUSD_JPY%2CAUD_USD%2CEUR_JPY%2CGBP_USD%2CGBP_JPY"])
          process (.start process-builder)
          reader (io/reader (.getInputStream process))]
      (future (read-stream reader))
      process))

  (def curl-process (start-curl-process))

;; To stop the process
  (.destroy curl-process)


  (+ 1 2)
  )

(comment
;; EXPERIMENTAL STREAM DATA FROM STREAM ENDPOINT VIA CURL SUBPROCESS because clj-http and http-kit didn't work.
  (do
    (defn parse-json-line [line]
      (try
        (json/read-str line :key-fn keyword)
        (catch Exception e {})))

    (def last-heartbeat (atom (util/current-time-sec)))

    (defn process-line [line]
      (let [data (parse-json-line line)]
        (when (= (:type data) "HEARTBEAT")
          (println "Heartbeat received:" data) ;; Log heartbeats
          (let [heartbeat-time (Double/parseDouble (:time data))]
            (reset! last-heartbeat heartbeat-time)))))

    (defn read-stream [reader]
      (with-open [rdr reader]
        (doseq [line (line-seq rdr)]
          (println "Received line:" line)
          (process-line line))))

    (defn start-curl-process []
      (let [process-builder (ProcessBuilder. ["curl"
                                              "--no-buffer"
                                              "-H" "Authorization: Bearer 808b8c2978ded93c563bc420348788ab-00fba0cf47cf2456d8b4bfeb4c65c312"
                                              "-H" "Accept-Datetime-Format: UNIX"
                                              "https://stream-fxpractice.oanda.com/v3/accounts/101-001-5729740-001/pricing/stream?instruments=EUR_USD%2CUSD_CAD%2CUSD_JPY%2CAUD_USD%2CEUR_JPY%2CGBP_USD%2CGBP_JPY"])
            process (.start process-builder)
            reader (io/reader (.getInputStream process))]
        (future (read-stream reader))
        process))

    (defn restart-curl-process [curl-process]
      (println "Restarting curl process")
      (.destroy curl-process)
      (start-curl-process)
      (reset! last-heartbeat (util/current-time-sec)))

    (defn stream-stopped? []
      (> (util/current-time-sec) (+ 7.5 @last-heartbeat)))

    (def curl-process (atom (start-curl-process)))

    (defn monitor-and-restart-stream []
      (while true
        (Thread/sleep 1000) ;; Check every second
        (when (stream-stopped?)
          (swap! curl-process restart-curl-process))))

    (future (monitor-and-restart-stream)))

  )

(defn get-binance-api-data
  ([endpoint] (get-binance-api-data endpoint nil))
  ([endpoint instrument-config]
   (-> endpoint
       (build-binance-url (binancify-candles-instrument-config instrument-config))
       (get-api-data (headers/get-binance-headers)))))
