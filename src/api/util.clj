(ns api.util
  (:require
   [clj-http.client :as client]
   [env :as env]
   [clojure.data.json :as json]
   [clojure.core.async :as async]))

(defn is-crypto? [instrument]
  (clojure.string/includes? instrument "USDT"))

;; SEND GET PUT POST REQUESTS

(defn send-api-get-request
  ([url headers]
   (client/get url {:headers headers})
  ;;  (client/get url {:headers headers :content-type :octet-stream})
  ;;  (client/get url {:headers headers :content-type :json :throw-exceptions false})
  ;;  (client/get url {:headers headers :content-type :json :debug true})
   ))

(defn send-api-put-request [url options]
  (client/put url options))

(defn send-api-post-request [url options]
  ;; (client/post url (assoc options :debug true))
  ;; (client/post url options)
  (try (client/post url options) (catch Exception e (println "caught exception: " (.getMessage e)))))

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

(defn get-oanda-headers
  [] {:Authorization (str "Bearer " (env/get-oanda-api-key))
      :Accept-Datetime-Format "UNIX"})

(defn get-oanda-api-data
  ([endpoint] (get-oanda-api-data endpoint nil))
  ([endpoint instrument-config]
   (-> endpoint
       (build-oanda-url instrument-config)
       (get-api-data (get-oanda-headers)))))

(defn get-oanda-stream-data
  [endpoint]
  (let [response (send-api-get-request
                  (build-oanda-stream-url endpoint)
                  (get-oanda-headers))
        _ (println "response:" response)
        ch (async/chan)]
    (async/thread
      (with-open [reader (java.io.BufferedReader. (java.io.InputStreamReader. (:body response)))]
        (doseq [line (line-seq reader)]
          (println)
          (async/>!! ch line))))
    ch))
