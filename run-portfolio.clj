(load "load")
(println "Dependencies loaded!")

(println "Running portfolio update...")
(try
  (load "portfolio")
  (require '[constants])
  (let [result ((resolve 'portfolio/shoot-money-x-from-backtest-y)
                25
                ((resolve 'portfolio/run-backtest) constants/pairs-by-liquidity-oanda))]
    (println "Portfolio update completed successfully!")
    (println "Positions updated:" result))
  (catch Exception e
    (println "Error running portfolio update:" (.getMessage e))
    (println "Stack trace:" (.printStackTrace e)))) 