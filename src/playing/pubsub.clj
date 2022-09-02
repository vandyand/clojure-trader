(ns playing.pubsub
  (:require
   [clojure.core.async :refer [chan pub sub go-loop put! <!]]))

(def news (chan 1))
(def shouter (pub news :topics))

(def alice (chan 1))
(def bob (chan 1))
(def clyde (chan 1))

(sub shouter :celebrity-gossip alice)
(sub shouter :space-x bob)
(sub shouter :space-x clyde)

(go-loop [heard (<! alice)] (println "alice heard: " heard))
(go-loop [heard (<! bob)] (println "bob heard: " heard))
(go-loop [heard (<! clyde)] (println "clyde heard: " heard))

(put! news {:topics :celebrity-gossip :data "omg she's prego!"})
(put! news {:topics :space-x :data "omg we're landing!"})