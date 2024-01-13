(ns nean.server
  (:require 
   [ring.adapter.jetty :as jetty :as jetty]
   [compojure.core :refer :all]
   [compojure.route :as route]
   [nean.arena :as arena]))

(defroutes app-routes
  (GET "/" [] "Hello World")
  (route/not-found "Not Found"))

(defn -main []
  (jetty/run-jetty app-routes {:port 3000}))
