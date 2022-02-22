(ns v0_2_X.strindicator
  (:require [stats :as stats]
            [clojure.pprint :as pp]
            [v0_1_X.incubator.inputs :as inputs]
            [v0_1_X.incubator.strategy :as strat]))

(def practice-strindy {:inputs [{:id 0}
                                     {:inputs [{:id 0 :shift 0}]
                                      :fn #(+ 1 %)}
                                     {:inputs [{:id 0}
                                               {:inputs [{:id 0 :shift 0}]
                                                :fn #(+ % 1)}]
                                      :fn #(+ 1 %1 %2)}]
                            :fn (fn [& args] (reduce + args))})

(def practice-eur-stream [1.13104 1.12975 1.12947 1.12943 1.13064 1.13053 1.1306 1.13118 1.13106 1.13188 1.13174 1.13192 1.13174 1.13219 1.13126 1.13461 1.13462 1.13482 1.1346 1.13408 1.13558 1.13219 1.13548 1.13626 1.13588 1.13554 1.13596 1.13582 1.1358 1.13578 1.13553 1.13573 1.13521 1.13472 1.1346 1.1348 1.13539 1.13636 1.13754 1.13898 1.13774 1.13806 1.13852 1.13656 1.1363 1.13653 1.13654 1.13808 1.13744 1.1377 1.13905 1.1382 1.13736 1.1376 1.13728 1.13796 1.13818 1.13828 1.13363 1.13422 1.13566 1.13604 1.13752 1.13584 1.13614 1.13755 1.13656 1.13778 1.13594 1.13594 1.13694 1.13628 1.13593 1.13628 1.13642 1.13601 1.13625 1.13614 1.13637 1.13598 1.13682 1.1367 1.13675 1.13638 1.1366 1.13709 1.137 1.13758 1.1371 1.1361 1.13626 1.13602 1.13491 1.13482 1.13411 1.13259 1.13224 1.13302 1.13312 1.13249])
(def practice-rand-stream [0.8989331375674989 0.27821771758407665 0.7901816856143883 0.024299708216268923 0.7064438880088981 0.14289924514192043 0.6747376803809666 0.02032296491542762 0.922412365141704 0.9758712904585127 0.8107495675424301 0.2679255262159741 0.7505116905094257 0.8327514242229859 0.4002776421866573 0.9962611559967636 0.8931437681102099 0.621697277776901 0.38909745102403537 0.5196091437775294 0.7303868582039125 0.18593677008557163 0.09742233790081012 0.30047665625934994 0.17569408856325197 0.9280778495882999 0.6930418140862576 0.0508341014866015 0.15515114073557668 0.21914843481144075 0.9697968699134453 0.5563277658458127 0.8221397034165445 0.6644179637568888 0.44997746746206957 0.7530419260947385 0.8155430463345394 0.40840469474173513 0.9161413819685132 0.21235806462495133 0.09716831547732208 0.05307373645826041 0.09601790348043426 0.5966860475400247 0.16285002820525674 0.43608206202940136 0.37357362685962703 0.8373184796699675 0.7117377894573883 0.4700294940323281 0.07998180986813741 0.755385926718741 0.1795604844255867 0.47902494564871934 0.1301509995045469 0.5978675009717204 0.8941982495794222 0.9854793439079833 0.5136321305365602 0.49283748969952346 0.9956825466831543 0.6978885135530009 0.4231381287616034 0.1416058590079834 0.6777839018747878 0.5294699852084445 0.609573641919356 0.16013617641305622 0.7546355342140383 0.8378704428213393 0.8893862293846625 0.35810201131728603 0.03338074997315976 0.7177607085111416 0.5982156728033696 0.9011687516628569 0.4826204149700929 0.1009881722325755 0.18423044904084718 0.7405644909279965 0.7264763620084088 0.6230568955891437 0.0652059138670198 0.913730417458188 0.9653754707548929 0.7000579029009046 0.3353118066683908 0.3208175308464525 0.02719807350789505 0.026773512500359198 0.900741579790036 0.36402300943620025 0.8862236350144859 0.7545312983096168 0.14772930889832636 0.4002362186204733 0.6523457764390321 0.9364843331568082 0.30216450344811885 0.30219101754002375])

(defn pos-or-zero [num] (if (pos? num) num 0))

(defn solve-strindy-at-index [strindy current-ind]
  (if (contains? strindy :id)
    (let [stream-id (get strindy :id)
          target-ind (pos-or-zero (- current-ind (or (get strindy :shift) 0)))]
      (cond (= stream-id 0) current-ind
            (= stream-id 1) (get practice-eur-stream current-ind)
            (= stream-id 2) (get practice-rand-stream current-ind)))
    (let [strind-fn (get strindy :fn)
          strind-inputs (get strindy :inputs)]
      (if (number? strind-fn) strind-fn
          (let [solution (apply strind-fn (mapv #(solve-strindy-at-index % current-ind) strind-inputs))]
            (if (Double/isNaN solution) 0.0 (mod solution 1)))))))

;; (defn solve-strindy [strindy strindy-config]
;;   (mapv (partial solve-strindy-at-index strindy)
;;         (range (get strindy-config :num-data-points))))

;; (def solution (solve-strindy practice-strindy 10))

;; (println solution)


;;---------------------------------------;;---------------------------------------;;---------------------------------------;;---------------------------------------


(def one-arg-funcs (list
                    (with-meta #(Math/sin %) {:name "sin"})
                    (with-meta #(Math/cos %) {:name "cos"})
                    (with-meta #(Math/tan %) {:name "tan"})
                    (with-meta #(Math/log (Math/abs (+ Math/E %))) {:name "modified log"})))

(def many-arg-funcs
  [(with-meta (fn [& args] (apply + args)) {:name "+"})
   (with-meta (fn [& args] (apply * args)) {:name "*"})
   (with-meta (fn [& args] (apply max args)) {:name "max"})
   (with-meta (fn [& args] (apply min args)) {:name "min"})
   (with-meta (fn [& args] (stats/mean args)) {:name "mean"})
   (with-meta (fn [& args] (stats/stdev args)) {:name "stdev"})])

(def two-arg-funcs (cons (with-meta #(Math/pow %1 %2) {:name "pow"}) many-arg-funcs))

(defn get-strindy-config [num-strindies min-depth max-depth max-children subscription-ids]
  {:num-strindies num-strindies :min-depth min-depth :max-depth max-depth :max-children max-children :subscription-ids subscription-ids})


;; (defn binary-func [num-inputs] 
;;   (with-meta 
;;     (fn [& args] 
;;       (strat/solve-tree 
;;        (strat/make-tree (strat/get-tree-config 3 5 (strat/get-index-pairs num-inputs))) 
;;        [args])) 
;;     {:name "strat tree"}))

(defn make-strindy-recur
  ([config] (make-strindy-recur config 0))
  ([config current-depth]
   (if (and (>= current-depth (get config :min-depth)) (or (> (rand) 0.5) (= current-depth (get config :max-depth))))
     (rand-nth [{:id (rand-nth (get config :subscription-ids)) :shift (first (random-sample 0.5 (range)))} {:fn-name "rand constant" :fn (rand) :inputs []}])
     (let [max-children (get config :max-children)
           new-depth (inc current-depth)
           num-inputs (or (first (random-sample 0.5 (range 1 max-children))) max-children)
           inputs (vec (repeatedly num-inputs #(make-strindy-recur config new-depth)))
           func (cond
                  ;; (= current-depth 0) (binary-func num-inputs)
                  (= num-inputs 0) (rand)
                  (= num-inputs 1) (rand-nth one-arg-funcs)
                  (= num-inputs 2) (rand-nth two-arg-funcs)
                  (> num-inputs 2) (rand-nth many-arg-funcs))]
       {:fn-name (get (meta func) :name)
        :fn func
        :inputs inputs}))))

;; (def strindy-b (make-strindy-recur strindy-config))

;; (pp/pprint strindy-b)

;; (def solution 
;;  (solve-strindy 
;;   strindy-b 
;;   strindy-config))

;; (println solution)

;;---------------------------------------;;---------------------------------------;;---------------------------------------;;---------------------------------------

(defn get-strindy-fn-config [strindy-config]
  (let [strindy (make-strindy-recur strindy-config)
        name (strat/rand-suffix "strindy")]
    {:name name
     :fn (fn [x] (solve-strindy-at-index strindy x))}))

(defn get-strindy-streams-config [strindy-config num]
  (vec (repeatedly num #(get-strindy-fn-config strindy-config))))

(defn get-strindy-inputs-config [num-inception-streams num-intention-streams num-data-points strindy-config]
  (let [inception-streams-config (get-strindy-streams-config strindy-config num-inception-streams)
        intention-streams-config (get-strindy-streams-config strindy-config num-intention-streams)]
    (inputs/get-input-config num-data-points inception-streams-config intention-streams-config)))

(def strindy-config (get-strindy-config 10 4 5 6 [0 1 2]))

(def input-config (get-strindy-inputs-config 4 1 100 strindy-config))
;; (def input-config (inputs/get-sine-inputs-config 4 1 1000 10 0.1 0 100))
(def tree-config (strat/get-tree-config 2 6 (strat/get-index-pairs (count (get input-config :inception-streams-config)))))
(def strat1 (strat/get-populated-strat input-config tree-config))
;; (def strat2 (strat/get-populated-strat input-config tree-config))
;; (def strat3 (strat/get-populated-strat input-config tree-config))
;; (def strat4 (strat/get-populated-strat input-config tree-config))
(strat/plot-strats-and-inputs input-config strat1)