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

;; Get the JWT secret from environment variables or use a default for development
(def jwt-secret (or (System/getenv "JWT_SECRET") "default-dev-secret-change-in-production"))

;; Create JWT auth backend
(def auth-backend (backends/jws {:secret jwt-secret}))

;; In-memory user store for development/demo
;; In production, this would be replaced with database storage
(def users-store (atom {"admin" {:username "admin"
                                 :password (hashers/derive "admin-password")
                                 :email "admin@example.com"
                                 :roles #{:admin}}
                        "demo" {:username "demo"
                                :password (hashers/derive "demo-password")
                                :email "demo@example.com"
                                :roles #{:user}}}))

;; Function to create a JWT token for a user
(defn create-token [user]
  (let [claims {:user (:username user)
                :email (:email user)
                :roles (vec (:roles user))
                :exp (+ (System/currentTimeMillis) (* 1000 60 60 24))}] ; Token expires in 24 hours
    (jwt/sign claims jwt-secret)))

;; Function to validate a user during login
(defn validate-user [username password]
  (when-let [user (get @users-store username)]
    (when (hashers/check password (:password user))
      (dissoc user :password))))

;; Function to register a new user (for development/demo purposes)
(defn register-user [username password email]
  (if (contains? @users-store username)
    false ; User already exists
    (do
      (swap! users-store assoc username {:username username
                                         :password (hashers/derive password)
                                         :email email
                                         :roles #{:user}})
      true)))

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

;; Middleware to check if user has required roles
(defn wrap-roles [handler roles]
  (fn [request]
    (let [identity (:identity request)
          user-roles (set (get identity :roles []))]
      (if (some user-roles roles)
        (handler request)
        (-> (response/response (json/encode {:status "error" :message "Forbidden"}))
            (response/status 403))))))

;; Add database functions for user management in production
(defn init-auth-db! [db-spec]
  (try
    (println "Initializing auth tables...")

    ;; Create users table
    (jdbc/execute! db-spec
                   ["CREATE TABLE IF NOT EXISTS users (
          id SERIAL PRIMARY KEY,
          username VARCHAR(255) NOT NULL UNIQUE,
          password VARCHAR(255) NOT NULL,
          email VARCHAR(255) NOT NULL UNIQUE,
          created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        )"])

    ;; Create roles table
    (jdbc/execute! db-spec
                   ["CREATE TABLE IF NOT EXISTS roles (
          id SERIAL PRIMARY KEY,
          name VARCHAR(255) NOT NULL UNIQUE
        )"])

    ;; Create user_roles table for many-to-many relationship
    (jdbc/execute! db-spec
                   ["CREATE TABLE IF NOT EXISTS user_roles (
          user_id INTEGER REFERENCES users(id),
          role_id INTEGER REFERENCES roles(id),
          PRIMARY KEY (user_id, role_id)
        )"])

    ;; Insert default roles if they don't exist
    (jdbc/execute! db-spec
                   ["INSERT INTO roles (name) VALUES ('admin') ON CONFLICT (name) DO NOTHING"])
    (jdbc/execute! db-spec
                   ["INSERT INTO roles (name) VALUES ('user') ON CONFLICT (name) DO NOTHING"])

    ;; Insert default admin user if it doesn't exist
    (let [username "admin"
          admin-exists? (not (empty? (jdbc/query db-spec ["SELECT id FROM users WHERE username = ?" username])))]
      (when-not admin-exists?
        (let [admin-id (:id (first (jdbc/insert! db-spec :users
                                                 {:username username
                                                  :password (hashers/derive "admin-password")
                                                  :email "admin@example.com"})))
              admin-role-id (:id (first (jdbc/query db-spec ["SELECT id FROM roles WHERE name = 'admin'"])))
              user-role-id (:id (first (jdbc/query db-spec ["SELECT id FROM roles WHERE name = 'user'"])))]
          (jdbc/insert! db-spec :user_roles {:user_id admin-id :role_id admin-role-id})
          (jdbc/insert! db-spec :user_roles {:user_id admin-id :role_id user-role-id})
          (println "Created default admin user"))))

    (println "Auth tables initialized successfully")
    (catch Exception e
      (println "Error initializing auth tables:" (.getMessage e))
      (.printStackTrace e))))

;; Function to get user from database by username
(defn get-db-user [db-spec username]
  (try
    (let [user (first (jdbc/query db-spec ["SELECT u.id, u.username, u.password, u.email 
                                            FROM users u 
                                            WHERE u.username = ?" username]))
          roles (when user
                  (jdbc/query db-spec ["SELECT r.name 
                                        FROM roles r 
                                        JOIN user_roles ur ON r.id = ur.role_id 
                                        WHERE ur.user_id = ?" (:id user)]))]
      (when user
        (assoc user :roles (set (map :name roles)))))
    (catch Exception e
      (println "Error getting user from database:" (.getMessage e))
      nil)))

;; Function to validate user from database
(defn validate-db-user [db-spec username password]
  (when-let [user (get-db-user db-spec username)]
    (when (hashers/check password (:password user))
      (dissoc user :password))))

;; Function to register a new user in the database
(defn register-db-user [db-spec username password email]
  (try
    (jdbc/with-db-transaction [tx db-spec]
      (let [user-exists? (not (empty? (jdbc/query tx ["SELECT id FROM users WHERE username = ? OR email = ?" username email])))]
        (if user-exists?
          false ; User already exists
          (let [user-id (:id (first (jdbc/insert! tx :users
                                                  {:username username
                                                   :password (hashers/derive password)
                                                   :email email})))
                user-role-id (:id (first (jdbc/query tx ["SELECT id FROM roles WHERE name = 'user'"])))]
            (jdbc/insert! tx :user_roles {:user_id user-id :role_id user-role-id})
            true))))
    (catch Exception e
      (println "Error registering user in database:" (.getMessage e))
      false)))

;; Authentication middleware function to apply to routes
(defn add-auth-middleware [routes]
  (-> routes
      (wrap-authentication auth-backend)
      (wrap-authorization auth-backend)))