(ns binance_security
  (:require
   [api.util :as api-util]
   [env :as env]
   [util :as util]
   [api.headers :as headers]))

(defn bytes->string [bytes]
  (apply str (map #(format "%x" %) bytes)))

(defn hmacsha256 [key val]
  (let [mac (javax.crypto.Mac/getInstance "HMACSHA256")
        secretKey (javax.crypto.spec.SecretKeySpec. (.getBytes key) (.getAlgorithm mac))]
    (-> (doto mac
          (.init secretKey)
          (.update (.getBytes val)))
        .doFinal
        bytes->string)))


(do
  (def sig-key (env/get-sensitive-data :BINANCE_API_SECRET))
  
  (def instrument-config {:symbol "BTCUSD"
                          :side "BUY"
                          :type "MARKET"
                          :quoteOrderQty "10.00"
                          :recvWindow 10000
                          :timestamp (util/current-time-msec)})

  (def sig-val (api-util/format-query-params
                instrument-config))

  (def signature (hmacsha256 sig-key sig-val))

  (api-util/send-api-post-request
   (api-util/build-binance-url
    "order"
    (assoc instrument-config :signature signature))
   (headers/get-binance-headers)))