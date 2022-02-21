### Mon, Feb 21, 22

Currently strategy trees from v0.1.x are solved by taking in inception and intention streams. These streams aren't fetched/calculated in real time like strindicator streams are. What are we switching out here?Basically the strindicators are replacing the randome sine functions for inception streams. We can make this work but is this ideal? What do we want the final setup to look like? Previously we had envisioned the decision tree strategy sitting on top of the strindicator tree as the parent node and just solving everything one time slice at a time. We should probably do it this way going forward because this is how it will be solved in real life, one time step at a time.

How would we do this though? I guess we're doing it already in the strindicator.... but not in the strategy tree solver. It's probably arbitrary when we fetch or calculate the inception stream values. The base tree solver solves for one instantanious input set at a time anyways and the whole strategy solver just zips up the inceptions streams into a stream of instant inputs and maps the solver over it. Iit's arbitrary to zip them and solve for them one at a time (obviously there might be performance considerations but conceptually it's arbitrary).

How doo we lay this out then? What are next steps? Refactor the v0.1 incubator strategy to solve one at a time inputs? No matter what we're mapping over a range of length :num-data-points. This is the "ultimate" input. Instrument inceptions stream values are all fetched by these indexes and generated inception streams are all generatd from this input. It's the global "map" in that way. Make the strategies/strindicators able to solve for any step on this map (knowing the previous values as well). This is a proxy for time itself which is inherent in every stream. We are dealing with time series after all! Or shall we say, time streams... This is to say, everything is based on the global time axis.

It might be nice to encode the random sine waves into the stindicators. We'd like to solve the strindicators one time step at a time which is entirely possible. It's also possible to encode the sine waves data in the strindicator. Perhaps it's best to just leave the sine data out for now as discussed in the previous post from Saturday, Feb 19. We can always add in the sine wave functions and other indicators like moving average later. For now just focus on getting a sieve stream and return stream (per instant time step) from the strindicators.

Really, any binary function could be used as the "head" of the strindicator. The whole tree ought to return binary but there's arbitrary ways of doing that, >/< being the most obvious which is why > is used in the decision tree solver in strategy currently. We could even return constant numbers between 0 and 1 for position sizing or between -1 and 1 for long and short position sizing. Using remainder of (/ % 2) (like mod 2) would be one way of scaling it... Something like that.

### Sat, Feb 19, 22

The random sine waves we are generating in 0.1.X incubator can be created in our strindy as it stands, and the same applies for a Moving Average indicator (for example). This being said, it is highly unlikely that these will ever be created randomly or even in a GA searching process. Is this ok? Try it out and see. There may come a point in the future where we force some structure into (onto?) our strindicators.

### Fri, Feb 18, 22

What to do next? How do we want strindicator to work? Are we constraining the strindicator functions at all? The only constraint is that they all return continuous values and the last one (parentmost one) returns binary. This is basically a nerual net with different types of activation functions. Instead of just relu or tanh or what have you we're using literally anything.

The parentmost node can use a decision tree to return binary. We need some way of collapsing multiple continuous values into binary which implies the need for if else logic (which is a decision).

Previously we were only modifying this parent node to the strindicator in the ga (which is fine). There's more power/potential though in modifying the entire strindicator tree.

What's the best way to construct these things though? We're generating random functions? They must return continuous values though, and not error out (so no divide by zero for example). How do we ensure these functions we're generating are compliant? We should test them before allowing them to be used? There are some families of functions that we know are compliant like sin and cos functions (and all other trig functions?) and add and multiply. So just use those? Let's just use (elementary functions)[https://en.wikipedia.org/wiki/Elementary_function] for now. That is constants, addition, multiplication, rational powers, exponentials, logarithms, trigonometric and hyperbolic functions.

### Thu, Feb 17, 22

Working on 0.2.0

#### Using Straticators:

tree-config is the blueprint for creating decision-tree (binary) strindicators
input-config contains blueprints for (continuous) strindicators as inputs to (binary) strindicators. In this sense, it's strindicators all the way down (which is fine and dandy (literally)).
So, strindicator config is everything that is necessary for building a strindicator. Just put a key in there for return type which will define whether the strindicator is a strategy or an indicator. This works right?
What do we need then, in order to build a strindicator? We need the strindicator function and the input stream(s). A sine wave strindicator only needs the x-axis as input (once it's args are defined of course. You could say the args are inputs but meh, not loving. Just define the thing). It's args must be defined somewhere else in the config, namely in the function itself.

#### Straticator Schema

Straticator schema: {:fn function :inputs [...inputs]}. Recursive because inputs are potentially generated from other strindicators.

The x-axis is assumed. For our purposes it is just the index of the input stream(s) which the function is currently evaluating (the instantanious inputs as it were) (which is just an incrementing integer series).

Therefore, to create a strindicator, all one needs is the strindicator config. Whether it's a strategy or an indicator can be determined by the function retun values. If the strindicator function returns continuous values (besides simple binary) the strindicator is defined as an indicator. If the strindicator function returns only 0 or 1 (binary) it is either a strategy or an indicator.

#### Straticators are Recursive

inputs are streams. input streams are either subscription streams (streams such as instruments which are ingested from outside the system) or generated streams (streams which are generated from zero or more subscription streams). Generated streams are strindicators. The definition of a strindicator is recursive. Therefore we need to create some base strindicators (or inputs rather... see below) from which all others may be derived (to avoid infinite recursion).

This also implies that strindicator config is recursive.

Straticator functions can subscribe to previous values of input streams. The current value of an input stream and all previous values are fair game as instantanious inputs.

A strindicator function is a recursive composition of other strindicator functions.

The inputs are either the presumed index (x-axis) (incrementing integer series) or a subscribed data stream (array of {value at x index}) which is essentially a values (prices or whatever) stream where the index is the presumed x-axis (integer series') value.

For what it's worth, it has been shown that one can find fitting patterns (rising/profitable return streams) from intention streams (subscription streams) without using any subscription streams as input (that is, only using the x-axis and values generated from these using, say, random sine waves).

### Todo:

Make a recursive strindicator config generator. This will take in a set of inputs which each function in the strindicator function tree can subscribe to. To begin, use the integer series as the only input. After that, get it working with subscription inputs.
