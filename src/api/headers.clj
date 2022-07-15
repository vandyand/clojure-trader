(ns api.headers
  (:require
   [env :as env]))

;; HEADER FUNCTIONS

(defn get-oanda-headers 
  [] {:Authorization (str "Bearer " (env/get-oanda-api-key)) 
      :Accept-Datetime-Format "UNIX"})

(defn get-binance-headers 
  [] {:X-MBX-APIKEY  (env/get-sensitive-data :BINANCE_API_KEY)})
