(ns nean.server
   (:require
    [ring.adapter.jetty :as jetty]
    [compojure.core :as cj]
    [compojure.route :as route]
    [nean.arena :as arena]
    [ring.util.response :as response]
    [cheshire.core :as json]
    [util :as util]
    [api.oanda_api :as oapi]
    [clojure.edn :as edn]))

 (defn req->body [req]
   (json/decode (-> req :body slurp) true))
 
 (cj/defroutes app-routes
   (cj/GET "/" [] (str "Hello World! Time: " (System/currentTimeMillis)))

   (cj/GET "/trade-env" [] (str (env/get-live-or-demo)))

  ;; Endpoint for getting accounts
   (cj/GET "/accounts" []
     (try
       (let [accounts (oapi/get-account-ids)]
         (response/response (json/encode {:status "success" :data accounts})))
       (catch Exception e
         (response/response (json/encode {:status "error" :message (.getMessage e)})))))

  ;; Endpoint for getting backtest ids
   (cj/GET "/backtest-ids" []
     (try
       (let [backtest-ids (arena/get-backtest-ids)]
         (response/response (json/encode {:status "success" :data backtest-ids})))
       (catch Exception e
         (response/response (json/encode {:status "error" :message (.getMessage e)})))))

  ;; Endpoint for getting backtest by id
   (cj/GET "/backtest/:id" [id]
     (try
       (let [backtest (arena/backtest-id->backtest id)]
         (if backtest
           (response/response (json/encode {:status "success" :data backtest}))
           (response/response (json/encode {:status "error" :message "Backtest not found"}))))
       (catch Exception e
         (response/response (json/encode {:status "error" :message (.getMessage e)})))))

  ;; Endpoint for backtesting
   (cj/POST "/backtest" req
     (try
       (let [body (req->body req)
             result (arena/backtest body)]
         (response/response (json/encode {:status "success" :data result})))
       (catch Exception e
         (response/response (json/encode {:status "error" :message (.getMessage e)})))))

  ;; Endpoint for live trading
   (cj/POST "/trade" req
     (try
       (let [body (req->body req)
             account-id (:account-id body)
             regularity (:regularity body)
             _ (if account-id
                 (if regularity
                   (arena/trade (:backtest-id body) account-id regularity)
                   (arena/trade (:backtest-id body) account-id))
                 (arena/trade (:backtest-id body)))]
         (response/response (json/encode {:status "success"})))
       (catch Exception e
         (response/response (json/encode {:status "error" :message (.getMessage e)})))))

  ;; Endpoint for stopping live trading
   (cj/POST "/stop-trading" req
     (try
       (let [body (req->body req)
             result (arena/stop-trading (:account-id body))]
         (response/response (json/encode {:status "success" :data result})))
       (catch Exception e
         (response/response (json/encode {:status "error" :message (.getMessage e)})))))

  ;; Endpoint for stopping live trading
   (cj/POST "/stop-all-trading" _
     (try
       (let [result (arena/stop-all-trading)]
         (response/response (json/encode {:status "success" :data result})))
       (catch Exception e
         (response/response (json/encode {:status "error" :message (.getMessage e)})))))

  ;; Endpoint for closing open positions of account
  (cj/POST "/close-positions" req
    (try
      (let [body (req->body req)
            result (oapi/close-positions (:account-id body))]
        (response/response (json/encode {:status "success" :data result})))
      (catch Exception e
        (response/response (json/encode {:stats "error" :message (.getMessage e)})))))
    
  ;; Endpoint for closing all open positions
    (cj/POST "/close-all-positions" _
      (try
        (let [result (oapi/close-all-positions)]
          (response/response (json/encode {:status "success" :data result})))
        (catch Exception e
          (response/response (json/encode {:status "error" :message (.getMessage e)})))))

    (route/not-found "Not Found"))

(defn -main []
  (future (jetty/run-jetty app-routes {:port 3000})))

(-main)
