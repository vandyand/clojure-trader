(ns auth.core
  (:require
   [buddy.sign.jwt :as jwt]
   [buddy.auth :refer [authenticated?]]
   [buddy.auth.backends :as backends]
   [buddy.auth.middleware :refer [wrap-authentication wrap-authorization]]
   [buddy.hashers :as hashers]
   [clojure.java.jdbc :as jdbc]
   [ring.util.response :as response]
   [cheshire.core :as json]))

(println "Loading stub auth.core from classes directory")

;; Get the JWT secret from environment variables or use a default for development
(def jwt-secret (or (System/getenv "JWT_SECRET") "default-dev-secret-change-in-production"))

;; Create JWT auth backend
(def auth-backend (backends/jws {:secret jwt-secret}))

;; Function to create a JWT token for a user
(defn create-token [user]
  (let [claims {:user (:username user)
                :email (:email user)
                :roles (vec (:roles user))
                :exp (+ (System/currentTimeMillis) (* 1000 60 60 24))}] ; Token expires in 24 hours
    (jwt/sign claims jwt-secret)))

;; Function to validate a user from database
(defn validate-db-user [db-spec username password]
  (println "Stub validate-db-user called")
  {:username username
   :email (str username "@example.com")
   :roles #{"user"}})

;; Function to register a new user in the database
(defn register-db-user [db-spec username password email]
  (println "Stub register-db-user called")
  true)

;; Middleware to ensure a route is authenticated
(defn wrap-authenticated [handler]
  (fn [request]
    (if (authenticated? request)
      (handler request)
      (-> (response/response (json/encode {:status "error" :message "Unauthorized"}))
          (response/status 401)))))

;; Function to extract user from request
(defn get-user-from-request [request]
  (get-in request [:identity :user]))

;; Add database functions for user management in production
(defn init-auth-db! [db-spec]
  (println "Stub init-auth-db! called"))

;; Authentication middleware function to apply to routes
(defn add-auth-middleware [routes]
  (-> routes
      (wrap-authentication auth-backend)
      (wrap-authorization auth-backend)))

;; Function to get user from database by username
(defn get-db-user [db-spec username]
  (println "Stub get-db-user called for username:" username)
  {:id 1
   :username username
   :password "hashed-password"
   :email (str username "@example.com")
   :roles #{"user"}}) 