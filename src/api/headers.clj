(ns api.headers
  (:require
   [env :as env]))

;; HEADER FUNCTIONS

(defn get-oanda-headers 
  [] {:Authorization (str "Bearer " (env/get-sensative-data :OANDA_API_KEY)) 
      :Accept-Datetime-Format "UNIX"})

(defn get-binance-headers 
  [] {:X-MBX-APIKEY  (env/get-sensative-data :BINANCE_API_KEY)})
