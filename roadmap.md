# Roadmap and Such and So

### Todo

- [ ] (0.2.x) Work on arena v1 - No live trading (practice or live) only mock trading.
  - [ ] Create stream bank - refactor inputs-config to subscribe to streams
  - [ ] Setup mock strategy infrastructure (0.2.0)
    - Create mock strategy with input data, tree data, target instrument data
  - [ ] Package strategies from incubator (0.2.1)
  - [ ] Run mock strategy (0.2.2)
- [ ] (0.3.0) Refactor csv_instrument and oanda_instrument implementation. Codify commonalities into a function in ga.

### Continuous

- [ ] Learn macros and start using them throughout. Embrace the power of clojure.
- [ ] Learn `core.async` and start using it throughout. Embrace the power of clojure.

### Nice to haves

- [ ] Spec one function
- [ ] Fuzz test one function with spec generator
- [ ] Spec all functions
- [ ] Fuzz test all functions with spec generators
- [ ] Use clojure.edn for config data
- [ ] Refactor `/incubator` to use `core.async` for performance boost with parallel processing.
- [ ] Refactor `/incubator` by config type (input, tree, population, ga)
- [ ] Performance: Store outside data streams in local db. Test if this is a performance boost (enough data and logically it will be)

### Completed Tasks

- [x] Start using versioning with [SemVer](https://semver.org/) (Feb 10, 22)
- [x] (0.1.0) Refactor `strategy.clj` and `vec_strategy.clj`
- [x] (0.1.1) Refactor `ga-config` to not include input and target data, but only paramaters for the data
  - Lazy load input and target data
  - Make sure GA still works
- [x] (0.1.2) Use formatter
- [x] (OLD 0.1.3 : NO CHANGE NEEDED -- SKIPpED) Memoize sine function (:fn item returned from `get-random-sine-config`) and check if performance boost
  - Test current, then memoize, then test again.
- [x] (0.1.3) Make strategy able to take multiple targets as input. Return stream will be sum of returns of each
  - We are not losing any functionality here, only gaining functionality.
- [x] (0.1.3-fix) Regression fix ga

### Completed Nice to haves
