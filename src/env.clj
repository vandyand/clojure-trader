(ns env
  (:require
   [clojure.data.json :as json]
   [env :as env]))

(defn get-sensative-data [keywd]
  ((json/read-str (slurp ".sensative.json") :key-fn keyword) keywd))

(defn get-env-data [keywd]
  ((json/read-str (slurp ".env.json") :key-fn keyword) keywd))