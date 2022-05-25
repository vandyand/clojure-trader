(ns playing.playing
  (:require [clojure.pprint :as pp]
            [clojure.data.json :as json]
            [clojure.java.io :as io]
            [clj-http.client :as client]
            [clojure.core.async :as async]
            [util :as util]
            [env :as env]))

(let [c (async/chan 2)]
  (async/thread (doseq [x (range 5)]
                  (async/>!! c x)
                  (println "putting value " x " on channel")))
  (async/thread
    (Thread/sleep 1000)
    (doseq [x (range 5)]
      (println "from chan " (async/<!! c)))))

(let [c (async/chan)]
  (async/thread
    (async/put! c "this string" (fn [sent?] (println "has been sent? " sent?))))
  (async/thread
    (async/take! c (fn [val] (println "taken = " val)))))


(let [c (async/chan 2)]
  (async/go (doseq [x (range 5)]
              (async/>! c x)
              (println "putting value " x " on channel!")))
  (async/go
    #_(Thread/sleep 1000)
    (doseq [x (range 5)]
      (println "taking " (async/<! c) " from channel!"))))


(defn fetch-user [user-id]
  (Thread/sleep 1000)
  (-> (str "https://reqres.in/api/users/" user-id)
      client/get
      :body
      json/read-json
      :data))

(defn email-user [email]
  (println "Email sent to " email))

(defn process-users []
  (let [c (async/chan)]
    (async/thread
      (doseq [x (range 1 5)]
        (async/>!! c (fetch-user x))))
    (async/thread
      (loop []
        (when-some [user (async/<!! c)]
          (email-user (:email user)))
        (recur)))))

(defn process-users-go []
  (let [c (async/chan)]
    (async/go
      (doseq [x (range 1 5)]
        (async/>! c (fetch-user x))))
    (async/go-loop []
      (when-some [user (async/<! c)]
        (email-user (:email user))
        (recur)))))

(def users-channel (async/chan))

(defn process-users-go-chan [channel]
  (async/go
    (doseq [x (range 1 5)]
      (async/>! channel (fetch-user x))))
  (async/go-loop []
    (when-some [user (async/<! channel)]
      (email-user (:email user))
      (recur))))

(process-users-go-chan users-channel)

(async/close! users-channel)

;------------------------------------;------------------------------------;------------------------------------

(def a (atom 0))

(def file-channel (async/chan))

(async/go
  (with-open [reader (clojure.java.io/reader "data/streams/EUR_USD-M15.edn")]
    (doseq [line (line-seq reader)]
      (async/>! file-channel line))))

(async/go-loop
 []
  (when-some [line (clojure.edn/read-string (async/<! file-channel))]
    (println (get line :time-stamp) (= (get line :time-stamp) 1651866177))
    (if (= (get line :time-stamp) 1651866177)
      (swap! a (fn [_ x] x) (get line :time-stamp)))
    nil)
  (recur))

@a

(async/close! file-channel)

;------------------------------------;------------------------------------;------------------------------------



(defn open-file-writer-async [chan full-file-name]
  (async/go
    (loop []
      (when (not (env/get-env-data :KILL_GO_BLOCKS?))
        (when-some [v (async/<! chan)]
          (with-open [wrtr (io/writer full-file-name :append true)]
            (.write wrtr (str v "\n"))))
        (recur)))))

(defn slow-thing [i]
  (Thread/sleep 1000)
  (let [data (repeat i (subs "abcdefghijklmnop" i (inc i)))]
   (println data)
  data))

(def print-chan (async/chan))

(open-file-writer-async print-chan "data/test.txt")

(dotimes [n 10]
  (async/go
    (async/>! print-chan (slow-thing n))))

(async/close! print-chan)

