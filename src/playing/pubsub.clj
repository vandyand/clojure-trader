(ns playing.pubsub
  (:require
   [clojure.core.async :as a]
   [util :as util]))

(def news (a/chan 1))
(def shouter (a/pub news :topics))

(def alice (a/chan 1))
(def bob (a/chan 1))
(def clyde (a/chan 1))

(a/sub shouter :celebrity-gossip alice)
(a/sub shouter :space-x bob)
(a/sub shouter :space-x clyde)

(a/go-loop [heard (a/<! alice)] (println "alice heard: " heard))
(a/go-loop [heard (a/<! bob)] (println "bob heard: " heard))
(a/go-loop [heard (a/<! clyde)] (println "clyde heard: " heard))

(a/put! news {:topics :celebrity-gossip :data "she's engaged!"})
(a/put! news {:topics :space-x :data "we're landing!"})


;;---------------------------------------------------------------------------------------------------------

