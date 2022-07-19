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
   :type _type
   :timeInForce time-in-force
   :positionFill "DEFAULT"})

(defn make-market-order-body [instrument units]
  {:order {:instrument instrument
           :units units
           :timeInForce "FOK"
           :type "MARKET"
           :positionFill "DEFAULT"}})

(defn make-limit-sltp-order-body [instrument units details]
  {:order {:instrument instrument
           :units units
           :price (details :price)
           :timeInForce "GTD"
           :gtdTime (details :cancel-time)
           :triggerCondition "DEFAULT"
           :type "LIMIT"
           :positionFill "DEFAULT"
           :stopLossOnFill {:price (details :sl-price)}
           :takeProfitOnFill {:price (details :tp-price)}}})

(defn make-market-price-order-body [instrument units price-bound]
  (let [order-body (make-market-order-body instrument units)]
    (assoc-in order-body [:order :priceBound] price-bound)))

(defn make-order-body [instrument units time-in-force gtd-time sl-price lim-price tp-price]
  (let [_type (if lim-price "LIMIT" "MARKET")
        base (make-base-order-body instrument units _type time-in-force)]
    {:order
     (cond-> base
        lim-price (assoc :price lim-price)
        (= time-in-force "GTD") (assoc :gtdTime gtd-time)
        sl-price (assoc :stopLossOnFill {:price sl-price})
        tp-price (assoc :takeProfitOnFill {:price tp-price})
        )}))

(defn get-sltp-prices 
  ([long? target-price sl-dist tp-dist]
  (let [sl-fn (if long? - +)
        tp-fn (if long? + -)]
    {:sl (sl-fn target-price sl-dist) 
     :tp (tp-fn target-price tp-dist)})))

(defn format-num-for-api [n precision]
  (-> n (util/round-dub precision) str))

(defn get-gtd-time [granularity]
  (let [start-time (oa/get-current-candle-open-time granularity)]
    (+ start-time (util/granularity->seconds granularity))))

(defn make-order-options-util
  ([instrument units] (make-order-options-util instrument units "FOK" nil nil nil))
  ([instrument units time-in-force granularity sl-dist tp-dist]
   (let [precision (oa/get-instrument-precision instrument)
         sltp? (and sl-dist tp-dist)
         long? (> units 0)
         target-price (when sltp? (oa/get-instrument-current-candle-open instrument granularity))
         sltp-prices (when sltp? (get-sltp-prices long? target-price sl-dist tp-dist))
         gtd-time (when (= time-in-force "GTD") (get-gtd-time granularity))
         formatted-price (when sltp? (format-num-for-api target-price precision))
         formatted-sl (when sltp? (format-num-for-api (sltp-prices :sl) precision))
         formatted-tp (when sltp? (format-num-for-api (sltp-prices :tp) precision))
         formatted-gtd-time (when gtd-time (str (int gtd-time)))
         formatted-units (str units)]
     (make-order-body instrument formatted-units time-in-force formatted-gtd-time formatted-sl formatted-price formatted-tp)
     )))

(comment

  
  (clojure.pprint/pprint (make-order-options-util "EUR_USD" 50))


  (clojure.pprint/pprint (make-order-options-util "EUR_USD" 50 "GTD" "H2" 0.005 0.005))
  
  )

+