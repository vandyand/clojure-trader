# Roadmap and Such and So

### Todo - short term

### Todo - longer term

- [ ] (0.3.X) Arena
  - [ ] Delete hystrindies from edn file by id if z-score is too low
  - [ ] Create Arena where ghystrindies trade via api on paper account
  - [ ] Add arena performance data and z-score to ghystrindies (becoming aghystrindies)
  - [ ] Good ones go live
  - [ ] Add live performacne data and z-score to aghystrindies (becoming laghystrindies)
- [ ] (0.4.X) Use `core.async` to leverage parallel processing (esp on alienware).
### Continuous

- [ ] Learn macros and start using them throughout. Embrace the power of clojure.
- [ ] Learn `core.async` and start using it throughout. Embrace the power of clojure.

### Nice to haves / Future features

- [ ] Spec one function
- [ ] Fuzz test one function with spec generator
- [ ] Spec all functions
- [ ] Fuzz test all functions with spec generators
- [ ] Use clojure.edn for config data
- [ ] Refactor `/incubator` and/or `/strindicator` to use `core.async` for performance boost with parallel processing.
- [ ] Make strategy configurable to go long or short (maybe get this working in incubator 0.1.x first)
- [ ] Make latex formula generator for strindies (and strategies? (logical latex notation)[https://www.geeksforgeeks.org/logic-notations-in-latex/])
- [ ] Update strindy ga crossover function to make it crossover branches further down than second level (so that potentially whole strindy2 tree could be grafted in to a low branch of strindy1). Same could be said for strat trees.
- [ ] Cleanup hydrate file names to be more idomatic
- [ ] Make strat tree solver (strat/solve-tree) drier (currently used in multiple files including v0.2 ga and edn)
- [ ] Get rid of :policy in strindicators, just put the key values on the first level with :inputs. There's no benefit to having these values in a lower level.
- [ ] Shorting ability (make sieve-stream ternary or just inverse intention stream or sieve stream or delta stream)
- [ ] Write actual functions to edn and decode them when reading instead of omitting them as we currently do
- [ ] Make edn file read/write ubiquitous that is, able to read/write objects of different types (hystrindies, ghystrindies... etc) (yet to be seen if this is necessary though probably will be)
- [ ] Cleanup backtest-config. inception-ids and intention-ids in strindy-config is derived data... Make more elegant somehow. Strindy config shouldn't be necessary in streams.edn
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
- [x] (0.2.9) Implement return type in make-strindy-recur
- [x] (0.2.9) Get multiple return streams from strindy - one for each intention stream (by applying sieve stream to it) plus one sum return stream
- [x] (0.2.10) Refactor oanda_strindicator to not need instrument config. It should pair well with 0_2_x config and populate. 
- [x] (0.2.10) Get strindicators working with oanda api data as inception and intension streams
- [x] (0.2.11) Standardize config throughout 0.2.x (see notes)
- [x] (0.2.11) Use constantly for rand constants in strindy trees (instead of the value itself).
- [x] (0.2.11) Make GA for strindicators.
  - [x] Make population
  - [x] Get fitnesses
  - [x] Get parents
  - [x] Get children
    - [x] Make mutators
    - [x] Make crossovers
  - [x] Repeat
  - [x] Get plotting working
- [x] (0.2.11) Make sure each hystrindy in ga has unique sieve stream
- [x] (0.2.12) Refactor hystrindy return streams to include deltas.
- [x] (0.3.0) Hystrindies write and read to/from edn file
- [x] (0.3.0) Streams write and read to/from edn file
- [x] (0.3.0) Somehow know where backtest data ends and gauntlet data starts
- [x] (0.3.1) Add gauntlet performance data and z-score to hystrindies (becoming ghystrindies)

### Completed Nice to haves
- [x] (0.2.8) Make strindicators able to subscribe to all config instruments as inception and intention data

### Utility loader command

(load "/v0_1_X/incubator/sine_waves" "/v0_1_X/incubator/inputs" "/v0_1_X/incubator/strategy" "/v0_1_X/incubator/ga")
(load "/v0_1_X/incubator/sine_waves" "/v0_1_X/incubator/inputs" "/v0_1_X/incubator/strategy" "/v0_2_X/strindicator")
(load "/v0_1_X/incubator/sine_waves" "/v0_1_X/incubator/inputs" "/v0_1_X/incubator/strategy" "/v0_1_X/incubator/ga" "/v0_1_X/arena/oanda_api" "/v0_1_X/arena/oanda_instrument")
