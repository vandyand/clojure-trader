(ns nean.server
  (:require
   [ring.adapter.jetty :as jetty]
   [compojure.core :as cj]
   [compojure.route :as route]
   [nean.arena :as arena]
   [ring.util.response :as response]
   [cheshire.core :as json]
   [util :as util]
   [api.oanda_api :as oapi]))

(cj/defroutes app-routes
  (cj/GET "/" [] (str "Hello World! Time: " (System/currentTimeMillis)))

  ;; Endpoint for backtesting
  (cj/POST "/backtest" req
    (let [_ (println "req:" req)
          body (json/decode (slurp (:body req)) true)
          _ (println "body:" body)]
      (try
        (let [result (arena/backtest body)]
          (response/response (json/encode {:status "success" :data result})))
        (catch Exception e
          (response/response (json/encode {:status "error" :message (.getMessage e)}))))))

  ;; Endpoint for live trading
  (cj/POST "/trade" req
    (let [body (json/decode (slurp (:body req)) true)]
      (try
        (let [_ (arena/trade (:granularity body))]
          (response/response (json/encode {:status "success"})))
        (catch Exception e
          (response/response (json/encode {:status "error" :message (.getMessage e)}))))))

  ;; Endpoint for stopping live trading
  (cj/POST "/stop-trading" _
    (try
      (let [result (arena/stop-trading)]
        (response/response (json/encode {:status "success" :data result})))
      (catch Exception e
        (response/response (json/encode {:status "error" :message (.getMessage e)})))))

  ;; Endpoint for closing all open positions
    (cj/POST "/close-positions" _
      (try
        (let [result (oapi/close-alll-positions (oapi/get-account-ids))]
          (response/response (json/encode {:status "success" :data result})))
        (catch Exception e
          (response/response (json/encode {:status "error" :message (.getMessage e)})))))
  
  (route/not-found "Not Found"))

(defn -main []
  (future (jetty/run-jetty app-routes {:port 3000})))

(-main)
