# Roadmap and Such and So

### Todo

- [ ] (0.1.2) Use formatter
- [ ] (0.1.3) Memoize sine function (strategy line ~124) and check if performance boost
- [ ] (0.1.4) Make strategy able to take multiple targets as input. Return stream will be sum of returns of each
  - We are not losing any functionality here, only gaining optionality.
- [ ] (0.2.0) Refactor `/incubator` by config type (input, tree, population, ga)
- [ ] (0.3.0) Refactor `/incubator` to use `core.async` for performance boost with parallel processing.
- [ ] (0.4.0) Refactor `/arena` to use `core.async` for api calls and whatnot.

### Continuous

- [ ] Learn macros and start using them throughout. Embrace the power of clojure.
- [ ] Learn `core.async` and start using it throughout. Embrace the power of clojure.

### Nice to haves

- [ ] Spec one function
- [ ] Fuzz test one function with spec generator
- [ ] Spec all functions
- [ ] Fuzz test all functions with spec generators

### Completed Tasks

- [x] Start using versioning with [SemVer](https://semver.org/) (Feb 10, 22)
- [x] (0.1.0) Refactor `strategy.clj` and `vec_strategy.clj`
- [x] (0.1.1) Refactor `ga-config` to not include input and target data, but only paramaters for the data
  - Lazy load input and target data
  - Make sure GA still works
