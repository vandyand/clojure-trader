# Roadmap and Such and So

### Next Doable ToDo
- [ ] clean up nean/arena.clj
- [ ] refactor nean/arena.clj - part of cleaning/refactoring initiative
- [ ] make starting and stopping trading easier by implementing an abstraction (agent) for this. 
### Initiatives

- [ ] make whole system automated
- automate metaparmeter tuning
- make a system for autoparameter tuning and then automate it

### Continuous

- [ ] Learn macros and start using them throughout. Embrace the power of clojure.
- [ ] Learn `core.async` and start using it throughout. Embrace the power of clojure.

### Nice to haves / Future features

- [ ] Make xindies able to subscribe to multiple input streams
- [ ] Save xindies shifts instead of keeping them all in memory with their performance. All we need is shifts and maybe back-score, fore-score and z-score
- [ ] Make xindies position sizes proportional to the timeframe they're trading
- [ ] Make a new system which incorporates multiple systems for enter long, enter short, long position size, short position size, exit long and exit short or some combination of them. Maybe some nerual nets?
- [ ] Spec one function
- [ ] Fuzz test one function with spec generator
- [ ] Spec all functions
- [ ] Fuzz test all functions with spec generators
- [ ] Use clojure.edn for config data
- [ ] Make latex formula generator for strindies (and strategies? (logical latex notation)[https://www.geeksforgeeks.org/logic-notations-in-latex/])
- [ ] Update strindy ga crossover function to make it crossover branches further down than second level (so that potentially whole strindy2 tree could be grafted in to a low branch of strindy1). Same could be said for strat trees.
- [ ] Make strat tree solver (strat/solve-tree) drier (currently used in multiple files including v0.2 ga and edn)
- [ ] Get rid of :policy in strindicators, just put the key values on the first level with :inputs. There's no benefit to having these values in a lower level.
- [O] Write actual functions to edn and decode them when reading instead of omitting them as we currently do
- [O] Make edn file read/write ubiquitous that is, able to read/write objects of different types (hystrindies, gaustrindies... etc) (yet to be seen if this is necessary though probably will be)
- [ ] Cleanup backtest-config. inception-ids and intention-ids in strindy-config is derived data... Make more elegant somehow. Strindy config shouldn't be necessary in streams.edn
- [ ] Feat: Get more than 5000 count of backtest data from api for input streams
- [ ] GA logging to see what mutations cause most success and success of mutations vs crossovers vs random
- [ ] Refactor back-streams to get rid of redundant data (when some stream is both inception and intention the data is currently duplicated which is unnecessary)
- [ ] Refactor back-hystrindieses in gauntlet to be vector of values of map instead of map - refactor gauntlet
- [ ] Don't use Thread/sleep in oanda_api requests lol. Use async or promise or something
- [ ] Refactor `fore?` in streams and hystrindies. Currently very redundant arg passing through many functions.
- [ ] Fix bug with solving gaustys with only one time slice of fore-data. Right now it bugs out with zero-index or something.
- [ ] Feat: ability to mix and match granualrities in inception and intention streams.
- [ ] Get multiple candidate hystrindies from GA instead of just the best one as is currently the case.

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
- [x] (0.3.1) Add gauntlet performance data and z-score to hystrindies (becoming gaustrindies)
- [x] (0.3.2) Organize data files in dedicated folder
- [x] (0.3.2) Added Arena
- [x] (0.3.2) Updated oanda_api for crud operations on trades by client id
- [x] (0.2.13) Refactor streams
- [x] (0.2.13) Get factory working with new streams refactor
- [x] (0.2.13) Get gauntlet working with new streams refactor
- [x] (0.3.3) Get runner working
- [x] (0.3.4) Fix sieve stream last index delta issue
- [x] (0.3.6) Added sharpe as fitness option for hystrindies
- [x] (0.3.8) Updated arena to run multiple good gausts
- [x] (0.3.8) Updated hystrindies to save to seperate files
- [x] (0.3.8) Added shift-data-points to streams for validation range
- [x] (0.3.8) Redid streams data file saving stuff
- [x] (0.3.8) run-arena working with multiple hyst files
- [x] (0.4.0) added async file writing and backtesting
- [x] (0.4.0) added laboratory
- [x] (0.4.0) started on binance api integration
- [x] (0.4.1) Use ohlc+v data instead of just open
- [x] (0.3.?) Go long and short - test with one intention instrument
- [x] (0.4.?) Refactor `/incubator` and/or `/strindicator` to use `core.async` for performance boost with parallel processing.
- [x] (0.3.?) Arena
  - [x] Create Arena where gaustrindies trade via api on paper account
  - [x] Add arena performance data and z-score to gaustrindies (becoming agaustrindies)
- [x] (0.4.?) Use `core.async` to leverage parallel processing (esp on alienware)
- [x] (0.5.X) Make crossover better (more intelligent somehow?) (Somehow make new type of strindicator with updateable params - much easier to mutate and crossover...)
### Completed Nice to haves
- [x] (0.2.8) Make strindicators able to subscribe to all config instruments as inception and intention data
