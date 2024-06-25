(ns api.headers
  (:require
   [env :as env]))

(defn get-oanda-headers
  [] {:Authorization (str "Bearer " (env/get-oanda-api-key))
      :Accept-Datetime-Format "UNIX"})
