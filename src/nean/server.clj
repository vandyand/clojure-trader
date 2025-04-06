(ns nean.server
  (:require
   [ring.adapter.jetty :as jetty]
   [ring.middleware.params :as params]
   [ring.middleware.json :refer [wrap-json-response wrap-json-body]]
   [ring.util.response :as response]
   [compojure.core :as compojure :refer [defroutes GET POST PUT DELETE]]
   [compojure.route :as route]
   [cheshire.core :as json]
   [clojure.string :as string]
   [ring.middleware.cors :refer [wrap-cors]]
   [nean.arena :as arena]
   [api.oanda_api :as oa]
   [env :as env])
  (:gen-class))

(defn req->body [req]
  (json/decode (-> req :body slurp) true))

(defroutes routes
  (GET "/" [] (str "Hello World! Time: " (System/currentTimeMillis)))

  (GET "/trade-env" [] (str (env/get-live-or-demo)))

  ;; Endpoint for getting accounts
  (GET "/accounts" []
    (try
      (let [accounts (oa/get-account-ids)]
        (response/response (json/encode {:status "success" :data accounts})))
      (catch Exception e
        (response/response (json/encode {:status "error" :message (.getMessage e)})))))

  ;; Endpoint for getting backtest ids
  (GET "/backtest-ids" []
    (try
      (let [backtest-ids (arena/get-backtest-ids)]
        (response/response (json/encode {:status "success" :data backtest-ids})))
      (catch Exception e
        (response/response (json/encode {:status "error" :message (.getMessage e)})))))

  ;; Endpoint for getting backtest by id
  (GET "/backtest/:id" [id]
    (try
      (let [backtest (arena/backtest-id->backtest id)]
        (if backtest
          (response/response (json/encode {:status "success" :data backtest}))
          (response/response (json/encode {:status "error" :message "Backtest not found"}))))
      (catch Exception e
        (response/response (json/encode {:status "error" :message (.getMessage e)})))))

  ;; Endpoint for backtesting
  (POST "/backtest" req
    (try
      (let [body (req->body req)
            result (arena/run-and-save-backtest body)]
        (response/response (json/encode {:status "success" :data result})))
      (catch Exception e
        (response/response (json/encode {:status "error" :message (.getMessage e)})))))

  ;; Endpoint for live trading
  (POST "/trade" req
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
  (POST "/stop-trading" req
    (try
      (let [body (req->body req)
            result (arena/stop-trading (:account-id body))]
        (response/response (json/encode {:status "success" :data result})))
      (catch Exception e
        (response/response (json/encode {:status "error" :message (.getMessage e)})))))

  ;; Endpoint for stopping live trading
  (POST "/stop-all-trading" _
    (try
      (let [result (arena/stop-all-trading)]
        (response/response (json/encode {:status "success" :data result})))
      (catch Exception e
        (response/response (json/encode {:status "error" :message (.getMessage e)})))))

  ;; Endpoint for closing open positions of account
  (POST "/close-positions" req
    (try
      (let [body (req->body req)
            result (oa/close-positions (:account-id body))]
        (response/response (json/encode {:status "success" :data result})))
      (catch Exception e
        (response/response (json/encode {:stats "error" :message (.getMessage e)})))))

  ;; Endpoint for closing all open positions
  (POST "/close-all-positions" _
    (try
      (let [result (oa/close-all-positions)]
        (response/response (json/encode {:status "success" :data result})))
      (catch Exception e
        (response/response (json/encode {:status "error" :message (.getMessage e)})))))

  (route/not-found "Not Found"))

;; Wrap the application with middleware
(def app-routes
  (-> routes
      params/wrap-params
      (wrap-cors :access-control-allow-origin [#".*"]
                 :access-control-allow-methods [:get :post :put :delete]
                 :access-control-allow-headers ["Origin" "X-Requested-With" "Content-Type" "Accept"])
      wrap-json-response
      wrap-json-body))

(defn -main []
  (let [port (Integer/parseInt (or (System/getenv "PORT") "3000"))]
    (println (str "Starting server on port " port))
    (jetty/run-jetty app-routes {:port port :join? false})))

;; Only call -main when running as a standalone application, not when required by other code
(when (= *file* (System/getProperty "babashka.file"))
  (-main))
