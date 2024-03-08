(ns main.frontend.app
  (:require [reagent.dom :as rdom]
            [reitit.frontend.easy :as rfe]
            [reitit.core :as r]))

(defn nav-menu []
  [:div
   [:a {:href "home"} "Home"]
   [:a {:href "backtest"} "Backtest"]
   [:a {:href "trade"} "Trade"]])

(defn home-page []
  [:div
   [nav-menu]
   "This is the home page"])

(defn backtest-page []
  [:div
   [nav-menu]
   "This is the backtest page"])

(defn trade-page []
  [:div
   [nav-menu]
   "This is the trade page"])

(def routes
  {"/" {:name :home
        :view home-page}
   "/home" {:name :home
        :view home-page}
   "/backtest" {:name :backtest
                :view backtest-page}
   "/trade" {:name :trade
             :view trade-page}})

(defn router []
  (let [router-instance (r/router routes)]
    (fn []
      (let [match (r/match-by-path router-instance (.-pathname js/location))]
        (if match
          ((:view (:data match)))
          [:div "Page not found"])))))

(defn init []
  (rdom/render [router] (js/document.getElementById "root")))
