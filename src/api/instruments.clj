;; (ns api.instruments
;;   (:require
;;    [api.binance_api :as bapi]
;;    [api.oanda_api :as oapi]))

;; (defn oanda-instrument? [instrument-config]
;;   (clojure.string/includes? (:name instrument-config) "_"))

;; (defn binance-instrument? [instrument-config]
;;   (not (oanda-instrument? instrument-config)))

;; (defn get-instrument-stream [instrument-config]
;;   (cond (oanda-instrument? instrument-config) (oapi/get-instrument-stream instrument-config)
;;         (binance-instrument? instrument-config) (bapi/get-instrument-stream instrument-config)))
