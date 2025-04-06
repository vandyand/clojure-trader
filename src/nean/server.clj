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
   [db.core :as db]
   [env :as env])
  (:gen-class))

;; Helper function to parse request bodies
(defn req->body [req]
  (try
    (if-let [body (:body req)]
      (do
        (println "Request body type:" (type body))
        (println "Raw request body:" body)
        (let [body-str (slurp body)
              parsed (json/parse-string body-str true)]
          (println "Body string:" body-str)
          (println "Parsed body:" parsed)
          parsed))
      (do
        (println "No body in request")
        {}))
    (catch Exception e
      (println "Error parsing request body:" (.getMessage e))
      (println "Stack trace:" (.printStackTrace e))
      {})))

;; Performance data collection function
(defn collect-performance-data []
  (try
    (println "Collecting performance data...")
    (let [accounts (oa/get-accounts)]
      (doseq [account accounts]
        (let [account-id (:id account)
              account-summary (oa/get-account-summary account-id)
              positions (oa/get-formatted-open-positions account-id)]
          ;; Save account performance
          (db/save-account-performance (:account account-summary))
          ;; Save position snapshots
          (doseq [position positions]
            (db/save-position-snapshot position account-id))))
      (println "Performance data collection completed."))
    (catch Exception e
      (println "Error collecting performance data:" (.getMessage e)))))

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

  ;; Endpoint for getting account summary
  (GET "/account-summary" []
    (try
      (let [summary (oa/get-account-summary)]
        (response/response (json/encode {:status "success" :data summary})))
      (catch Exception e
        (response/response (json/encode {:status "error" :message (.getMessage e)})))))

  ;; Endpoint for getting account summary for a specific account
  (GET "/account-summary/:account-id" [account-id]
    (try
      (let [summary (oa/get-account-summary account-id)]
        (response/response (json/encode {:status "success" :data summary})))
      (catch Exception e
        (response/response (json/encode {:status "error" :message (.getMessage e)})))))

  ;; Endpoint for getting open positions
  (GET "/open-positions" []
    (try
      (let [positions (oa/get-formatted-open-positions)]
        (response/response (json/encode {:status "success" :data positions})))
      (catch Exception e
        (response/response (json/encode {:status "error" :message (.getMessage e)})))))

  ;; Endpoint for getting open positions for a specific account
  (GET "/open-positions/:account-id" [account-id]
    (try
      (let [positions (oa/get-formatted-open-positions account-id)]
        (response/response (json/encode {:status "success" :data positions})))
      (catch Exception e
        (response/response (json/encode {:status "error" :message (.getMessage e)})))))

  ;; Endpoint for getting open trades
  (GET "/open-trades" []
    (try
      (let [trades (oa/get-open-trades)]
        (response/response (json/encode {:status "success" :data trades})))
      (catch Exception e
        (response/response (json/encode {:status "error" :message (.getMessage e)})))))

  ;; Endpoint for getting account performance history
  (GET "/performance/:account-id" [account-id days]
    (try
      (let [days-int (if days (Integer/parseInt days) 30)
            history (db/get-account-performance-history account-id days-int)]
        (response/response (json/encode {:status "success" :data history})))
      (catch Exception e
        (response/response (json/encode {:status "error" :message (.getMessage e)})))))

  ;; Endpoint for getting all accounts performance history
  (GET "/performance" [days]
    (try
      (let [days-int (if days (Integer/parseInt days) 30)
            history (db/get-all-accounts-performance-history days-int)]
        (response/response (json/encode {:status "success" :data history})))
      (catch Exception e
        (response/response (json/encode {:status "error" :message (.getMessage e)})))))

  ;; Endpoint for manually triggering performance data collection
  (POST "/collect-performance" []
    (try
      (collect-performance-data)
      (response/response (json/encode {:status "success" :message "Performance data collection started"}))
      (catch Exception e
        (response/response (json/encode {:status "error" :message (.getMessage e)})))))

  ;; Endpoint for getting latest price of an instrument
  (GET "/price/:instrument" [instrument]
    (try
      (let [price (oa/get-latest-price instrument)]
        (response/response (json/encode {:status "success" :data {:instrument instrument :price price}})))
      (catch Exception e
        (response/response (json/encode {:status "error" :message (.getMessage e)})))))

  ;; Endpoint for getting latest prices of multiple instruments
  (POST "/prices" req
    (try
      (let [body (req->body req)
            _ (println "Processed body:" body)
            instruments (:instruments body)]
        (println "Received instruments:" instruments)
        (if (and instruments (seq instruments))
          (let [prices (oa/get-latest-prices instruments)]
            (println "Retrieved prices:" prices)
            (response/response (json/encode {:status "success" :data prices})))
          (do
            (println "Invalid or missing instruments array")
            (response/response (json/encode {:status "error" :message "No instruments provided or invalid format. Expected {\"instruments\": [\"EUR_USD\", ...]}"})))))
      (catch Exception e
        (println "Error in prices endpoint:" (.getMessage e))
        (println "Stack trace:" (.printStackTrace e))
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

;; Setup a scheduled task to collect performance data
(def performance-collection-interval (* 60 60 1000)) ;; Every hour
(def performance-collection-thread (atom nil))

(defn start-performance-collection []
  (reset! performance-collection-thread
          (future
            (while true
              (try
                (collect-performance-data)
                (Thread/sleep performance-collection-interval)
                (catch Exception e
                  (println "Error in performance collection thread:" (.getMessage e))
                  (Thread/sleep 60000)))) ;; Wait a minute on error before trying again
            )))

(defn stop-performance-collection []
  (when-let [thread @performance-collection-thread]
    (future-cancel thread)
    (reset! performance-collection-thread nil)))

(defn -main []
  (let [port (Integer/parseInt (or (System/getenv "PORT") "3000"))]
    (println (str "Starting server on port " port))
    ;; Start performance data collection
    (start-performance-collection)
    ;; Add shutdown hook to stop collection when the JVM exits
    (.addShutdownHook (Runtime/getRuntime)
                      (Thread. ^Runnable stop-performance-collection))
    (jetty/run-jetty app-routes {:port port :join? false})))

;; Only call -main when running as a standalone application, not when required by other code
(when (= *file* (System/getProperty "babashka.file"))
  (-main))
