(ns playing.macros)

(defmacro infix [infixed]
  (list (second infixed) (first infixed) (last infixed)))

(infix (1 + 8))

(macroexpand '(infix (1 + 8)))

(defmacro infixx [[operand1 operation operand2]]
  (list operation operand1 operand2))

(infixx (2 + 5))

(macroexpand '(infixx (2 + 5)))

;;-------------------------------------------------------------------------------------------------------------------

(defmacro print-rtn [expression]
  (list 'let ['result expression]
        (list 'println 'result)
        'result))

(print-rtn "this expression here")

(macroexpand '(print-rtn "this expression here"))

;;-------------------------------------------------------------------------------------------------------------------


(defmacro plus2 [arg] (list '+ arg '(inc 1)))

(macroexpand '(plus2 2))

(plus2 2)


(defmacro plus3 [arg] `(+ ~arg (inc 2)))

(macroexpand '(plus3 2))

(plus3 2)

;;-------------------------------------------------------------------------------------------------------------------

(defmacro code-critic [bad good]
  (list 'do
        (list 'println "Gread squid of Madrid, this is bad code:" (list 'quote bad))
        (list 'println "Sweet gorilla of Manila, this is good code:" (list 'quote good))
        ))

(macroexpand '(code-critic (1 + 2) (+ 1 2)))

(code-critic (1 + 2) (+ 1 2))



(defmacro code-critic-nicer [bad good]
  `(do (println "Gread squid of Madrid, this is bad code:" (quote ~bad))
       (println "Sweet gorilla of Manila, this is good code:" (quote ~good))))

(code-critic-nicer (1 + 2) (+ 4 5))

;;-------------------------------------------------------------------------------------------------------------------

(defn criticize-code [criticism code]
  `(println ~criticism ~code))

(criticize-code "Code is good" '(+ 5 6))


;;-------------------------------------------------------------------------------------------------------------------


(defmacro do-multiple [& args]
  (for [arg args]
       `(println ~arg)))

(macroexpand '(do-multiple 2 4))

(do-multiple 2 3)

(defmacro x [a b]
  (list 'do `(println ~a) `(println ~b)))

(macroexpand '(x 23 45))

(x 2 34)

(defmacro xy [& args]
  (let [_form (for [arg args] `(println ~arg))]
    (cons 'do _form)))

(macroexpand '(xy 23 45))

(xy 2 43)

(defmacro xyz [& args]
  `(do ~@(for [arg args] (list 'println arg))))

(macroexpand '(xyz 4 3 87))

(xyz 4 3 87)

(let [x 234]
  (list 'println x))

(let [x 234]
  `(println ~x))

(let [x [234 345 456]]
  `(println ~@x))

;;-------------------------------------------------------------------------------------------------------------------

