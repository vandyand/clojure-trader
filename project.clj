(defproject clojure-trader "0.1.0-SNAPSHOT"
  :description "Clojure Trader backend"
  :url "https://github.com/yourusername/clojure-trader"
  :license {:name "Eclipse Public License"
            :url "http://www.eclipse.org/legal/epl-v10.html"}
  :min-lein-version "2.0.0"
  :dependencies [[org.clojure/clojure "1.11.1"]
                 [org.clojure/data.json "2.4.0"]
                 [org.clojure/data.csv "1.0.1"]
                 [org.postgresql/postgresql "42.6.0"]
                 [org.clojure/java.jdbc "0.7.12"]
                 [com.github.seancorfield/next.jdbc "1.3.894"]
                 [metasoarous/oz "1.6.0-alpha36"]
                 [ring/ring-core "1.9.6"]
                 [ring/ring-jetty-adapter "1.9.6"]
                 [ring/ring-json "0.5.1"]
                 [ring-cors "0.1.13"]
                 [compojure "1.7.0"]
                 [cheshire "5.11.0"]
                 [clj-http "3.12.3"]
                 [org.clojure/data.fressian "1.0.0"]
                 [buddy/buddy-core "1.7.1"]
                 [org.slf4j/slf4j-api "1.7.36"]
                 [org.slf4j/slf4j-simple "1.7.36"]
                 [buddy/buddy-auth "3.0.1"]
                 [buddy/buddy-sign "3.4.1"]
                 [buddy/buddy-hashers "1.8.1"]
                 [org.clojure/core.async "1.5.648"]]
  :main ^:skip-aot nean.server
  :source-paths ["src" "classes"]
  :resource-paths ["resources"]
  :aot [auth.core db.core migrations.core nean.server]
  :target-path "target/%s"
  :profiles {:uberjar {:aot :all
                       :jvm-opts ["-Dclojure.compiler.direct-linking=true"]}}) 