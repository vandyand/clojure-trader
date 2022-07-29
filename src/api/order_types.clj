(ns api.order_types
  (:require [api.oanda_api :as oa]
            [util :as util]))

;; type is market or limit
;; limit needs a price

;; stop loss needs a price (which can be derived from a distance and long-or-short)
;; take profit needs a price (which can be derived from a distance and long-or-short)

;; gtdTime needed if timeInForce is "GTD"

(defn make-base-order-body [instrument units _type time-in-force]
    {:instrument instrument
     :units units
     :type (or _type "MARKET")
     :timeInForce (or time-in-force "FOK")
     :positionFill "DEFAULT"})

(defn make-order-body [instrument units _type sl-price lim-price tp-price time-in-force gtd-time]
  (let [base (make-base-order-body instrument units _type time-in-force)]
    {:order
     (cond-> base
       (and (= _type "LIMIT") lim-price) (assoc :price lim-price)
       (= time-in-force "GTD") (assoc :gtdTime gtd-time)
       sl-price (assoc :stopLossOnFill {:price sl-price})
       tp-price (assoc :takeProfitOnFill {:price tp-price}))}))

(defn- price->pow [target-price]
  (as-> target-price $ (str $) (clojure.string/split $ #"[.]") (first $) (count $) (dec $) (Math/pow 10 $)))

(defn get-sltp-prices 
  ([long? target-price sl-dist tp-dist]
   (let [power (price->pow target-price) ;; This is to scale distances for JPY
         sl-fn (if long? - +)
         tp-fn (if long? + -)]
     {:sl (sl-fn target-price (* sl-dist power))
      :tp (tp-fn target-price (* tp-dist power))})))

(defn format-num-for-api [n precision]
  (-> n (util/round-dub precision) str))

(defn get-gtd-time [granularity]
  (let [start-time (oa/get-current-candle-open-time granularity)]
    (+ start-time (util/granularity->seconds granularity))))

(defn- make-formatted-options [instrument units _type sl-dist tp-dist granularity time-in-force]
  (let [sltp? (and sl-dist tp-dist)
        long? (> units 0)
        target-price (when (or (= _type "LIMIT") sltp?) (oa/get-instrument-current-candle-ohlc instrument granularity :c))
        sltp-prices (when sltp? (get-sltp-prices long? target-price sl-dist tp-dist))
        gtd-time (when (= time-in-force "GTD") (get-gtd-time granularity))
        precision (when (or (= _type "LIMIT") sltp?) (oa/get-instrument-precision instrument))
        formatted-price (when (= _type "LIMIT") (format-num-for-api target-price precision))
        formatted-sl (when sltp? (format-num-for-api (sltp-prices :sl) precision))
        formatted-tp (when sltp? (format-num-for-api (sltp-prices :tp) precision))
        formatted-gtd-time (when gtd-time (str (int gtd-time)))
        formatted-units (str units)]
     (make-order-body instrument formatted-units _type formatted-sl formatted-price formatted-tp time-in-force formatted-gtd-time)))

(defn make-order-options-util
  ([instrument units] (make-order-options-util instrument units nil))
  ([instrument units _type] (make-order-options-util instrument units _type nil nil))
  ([instrument units _type sl-dist tp-dist] (make-order-options-util instrument units _type sl-dist tp-dist nil nil))
  ([instrument units _type sl-dist tp-dist time-in-force granularity]
   (make-formatted-options instrument units _type sl-dist tp-dist granularity time-in-force)))

(comment


  (-> "EUR_USD"
      (make-order-options-util 50)
      clojure.pprint/pprint)


  (clojure.pprint/pprint (make-order-options-util "EUR_USD" 50 "MARKET" 0.005 0.005))
  
  )