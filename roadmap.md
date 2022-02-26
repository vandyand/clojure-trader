# Roadmap and Such and So

### Todo

- [ ] (0.2.x) Keep working on strindicators
  - [ ] Get strindicators working with oanda api data as inception and intension streams
  - [ ] Make GA for strindicators.
    - [ ] Make population
    - [ ] Get fitnesses
    - [ ] Get parents
    - [ ] Get children
      - [ ] Make mutators
      - [ ] Make crossovers
    - [ ] repeat
- [ ] Arena: Work on arena v1 - No live trading (practice or live) only mock trading.
  - [ ] Create stream bank - refactor inputs-config to subscribe to streams
  - [ ] Setup mock strategy infrastructure
    - Create mock strindicator with input data, tree data, target instrument data
  - [ ] Package strindicators from incubator
  - [ ] Run mock strindicator
- [ ] Refactor csv_instrument and oanda_instrument implementation. Codify commonalities into a function in ga.
- [ ] Cleanup strindicator

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
- [ ] Make strategy configurable to go long or short (maybe get this working in incubator 0.1.x first)
- [ ] Make latex formula generator for strindies (and strategies? (logical latex notation)[https://www.geeksforgeeks.org/logic-notations-in-latex/])

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
- [x] (0.2.0) Solve manually built strindicator working
- [x] (0.2.1) Build strindicator working
- [x] (0.2.2) Nodes should more frequently take one input (to create raw materials as it were)
- [x] (0.2.3) Get it working with EUR_USD as extra input
- [x] (0.2.4) Rename inputs config to sine inputs config because as it's currently used, it only supports random sine waves.
- [x] (0.2.5)
  - [x] Make parentmost node a compatable strategy tree
  - [x] Solve strindicators for intention stream(s) to create a return stream(s)
- [x] (0.2.6) Make strindicators compatable with binary tree nodes
- [x] (0.2.7) Get return streams from strindicators
### Completed Nice to haves

### Utility loader command

(load "/v0_1_X/incubator/sine_waves" "/v0_1_X/incubator/inputs" "/v0_1_X/incubator/strategy" "/v0_1_X/incubator/ga")
(load "/v0_1_X/incubator/sine_waves" "/v0_1_X/incubator/inputs" "/v0_1_X/incubator/strategy" "/v0_2_X/strindicator")
(load "/v0_1_X/incubator/sine_waves" "/v0_1_X/incubator/inputs" "/v0_1_X/incubator/strategy" "/v0_1_X/incubator/ga" "/v0_1_X/arena/oanda_api" "/v0_1_X/arena/oanda_instrument")
