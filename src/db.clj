(ns db
  (:require [next.jdbc :as jdbc]
            [next.jdbc.sql :as sql]
            [next.jdbc.result-set :as rs]
            [malli.core :as m]
            [malli.error :as me])
  (:import [java.time Instant]
           [java.sql Timestamp]
           [java.util UUID]))

(def db-spec {:dbtype "postgresql"
              :dbname "broker"
              :host "localhost"
              :port 5432
              :user "admin"
              :password "pass"})

(defn list-tables []
  (with-open [conn (jdbc/get-connection db-spec)]
    (let [result (jdbc/execute! conn ["SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"]
                                {:builder-fn rs/as-arrays})]
      (map first (rest result)))))

(defn get-table-schema [table-name]
  (with-open [conn (jdbc/get-connection db-spec)]
    {:table_name table-name
     :columns (jdbc/execute! conn [(str "SELECT column_name, data_type "
                                        "FROM information_schema.columns "
                                        "WHERE table_name = ?") table-name]
                             {:builder-fn rs/as-arrays})}))

(defn format-schema [{:keys [table_name columns]}]
  {:table_name table_name
   :columns (map (fn [[col-name col-type]]
                   {:name (keyword col-name)
                    :type col-type})
                 (rest columns))})

(defn get-formatted-table-schemas []
  (let [schemas (pmap get-table-schema (list-tables))]
    (map format-schema schemas)))

#_(get-formatted-table-schemas)


;; Multimethod to convert different types to java.sql.Timestamp
(defmulti to-timestamp class)

(defmethod to-timestamp Long [millis]
  (Timestamp/from (Instant/ofEpochMilli millis)))

(defmethod to-timestamp String [time-str]
  (Timestamp/from (Instant/parse time-str)))

;; Helper function to convert string to UUID
(defn to-uuid [uuid-str]
  (UUID/fromString uuid-str))

;; Define Malli schemas
(def TimeIndexSchema
  [:map
   [:time any?] ;; Expect Unix millisecond timestamp as an integer or ISO 8601 string
   [:record_type string?]
   [:record_id string?]]) ;; Expect UUID as a string

(def InstrumentDataSchema
  [:map
   [:id string?] ;; Expect UUID as a string
   [:time any?] ;; Expect Unix millisecond timestamp as an integer or ISO 8601 string
   [:instrument string?]
   [:open double?]
   [:high double?]
   [:low double?]
   [:close double?]
   [:volume double?]])

;; Validate data with Malli
(defn validate-data [schema data]
  (let [result (m/validate schema data)]
    (if result
      data
      (throw (ex-info "Invalid data" (me/humanize (m/explain schema data)))))))

;; Example function to insert a record
(defn create-record [table-name record schema]
  (let [record (validate-data schema record)
        record (-> record
                   (update :time to-timestamp)
                   (update :record_id to-uuid)
                   (update :id to-uuid))]
    (with-open [conn (jdbc/get-connection db-spec)]
      (sql/insert! conn table-name record))))

;; Function to get all records from the given table-name
(defn get-records [table-name]
  (with-open [conn (jdbc/get-connection db-spec)]
    (jdbc/execute! conn [(str "SELECT * FROM " table-name)])))


;; Example data for "time_index"
(def time-index-example
  {:time 1720645150253
   :record_type "example_type"
   :record_id "123e4567-e89b-12d3-a456-426614174000"})

(def time-index-example-2
  {:time "2024-07-10T00:00:00.000000000Z"
   :record_type "example_type"
   :record_id "123e4567-e89b-12d3-a456-426614174077"})



#_(create-record "time_index" time-index-example-2 TimeIndexSchema)

(def instrument-data-example
  {:id "123e4567-e89b-12d3-a456-426614174001"
   :time "2024-07-10T01:01:01.000000000Z"
   :instrument "example_instrument"
   :open 100.0
   :high 110.0
   :low 90.0
   :close 105.0
   :volume 1000.0})

#_(create-record "instrument_data" instrument-data-example)

(get-records "time_index")












(comment
  (defn to-unix-timestamp [time-str]
    (-> (Instant/parse time-str)
        (.getEpochSecond)))

;; Example function to insert a record
  (defn create-record [table-name record]
    (let [record (update record :time to-unix-timestamp)]
      (with-open [conn (jdbc/get-connection db-spec)]
        (sql/insert! conn table-name record))))

;; Example function to read a record
  (defn read-record [table-name id]
    (with-open [conn (jdbc/get-connection db-spec)]
      (sql/get-by-id conn table-name id)))

;; Example function to update a record
  (defn update-record [table-name id updates]
    (let [updates (update updates :time to-unix-timestamp)]
      (with-open [conn (jdbc/get-connection db-spec)]
        (sql/update! conn table-name updates {:id id}))))

;; Example function to delete a record
  (defn delete-record [table-name id]
    (with-open [conn (jdbc/get-connection db-spec)]
      (sql/delete! conn table-name {:id id})))

;; Example data for "time_index"
  (def time-index-example
    {:time "2023-10-01T12:00:00Z"
     :record_type "example_type"
     :record_id "123e4567-e89b-12d3-a456-426614174000"})

  (create-record "time_index" time-index-example)

;; Example data for "instrument_data"
  (def instrument-data-example
    {:id "123e4567-e89b-12d3-a456-426614174001"
     :time "2023-10-01T12:00:00Z"
     :instrument "example_instrument"
     :open 100.0
     :high 110.0
     :low 90.0
     :close 105.0
     :volume 1000.0})

;; Example data for "order_data"
  (def order-data-example
    {:id "123e4567-e89b-12d3-a456-426614174002"
     :time "2023-10-01T12:00:00Z"
     :instrument "example_instrument"
     :order_id "order123"
     :type "buy"
     :quantity 10.0
     :price 100.0
     :fee 1.0
     :status "completed"
     :usd_spent 1000.0
     :usd_fee 10.0
     :usd_total_spent 1010.0})

;; Example data for "position_data"
  (def position-data-example
    {:id "123e4567-e89b-12d3-a456-426614174003"
     :time "2023-10-01T12:00:00Z"
     :account_id "account123"
     :instrument "example_instrument"
     :quantity 50.0
     :entry_price 100.0
     :current_price 105.0
     :status "open"})

;; Example data for "account_data"
  (def account-data-example
    {:id "123e4567-e89b-12d3-a456-426614174004"
     :time "2023-10-01T12:00:00Z"
     :account_id "account123"
     :balance_position_id "123e4567-e89b-12d3-a456-426614174005"
     :overall_value 5000.0
     :positions {:position1 {:id "123e4567-e89b-12d3-a456-426614174006"
                             :quantity 10.0
                             :value 1000.0}
                 :position2 {:id "123e4567-e89b-12d3-a456-426614174007"
                             :quantity 20.0
                             :value 2000.0}}}))