(ns arena.live_data
  (:require [clj-http.client :as client]
            [clojure.data.json :as json]))

(def test-url "https://jsonplaceholder.typicode.com/posts/1")
(def test-response (json/read-str (:body (client/get test-url)) :key-fn keyword))

(def oanda-url "https://api-fxpractice.oanda.com/v3/")

(defn get-sensative-data [keywd]
  ((json/read-str (slurp ".sensative.json") :key-fn keyword) keywd))

(def bearer (str "Bearer " (get-sensative-data :OANDA_API_KEY)))
(def headers {:headers {:Authorization bearer}})

(defn get-endpoint [endpoint]
  (client/get (str oanda-url endpoint) headers))

(defn parse-response-body [response]
  (json/read-str (response :body) :key-fn keyword))

(def accounts (parse-response-body (get-endpoint "accounts")))

