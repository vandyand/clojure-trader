### Tues, July 19, 22
Time for cleanup! Unfinished projects:
 - limit/market orders with sl/tp
 - Binance API
 - GPU programming
 - Multiple instances
In order to complete these tasks we need a clean (loved) code base. Dig in and clean up.
Being able to generate data structures (like gausts or hysts) would be great. This can be done using spec.

### Fri, July 15, 22
Need to be faster. Use the GPU. The results (how many "hits" you get for 100 backtests for example) has high variance. This is essentially noise that degrades(?) performance. A less noisy signal will be found by running more backtests to get more gausts and finding the robust ones. Another option is to just run one instrument instead of 20 and get lots more results for that one but this is dumb. The idea is ubiquty. At some point we'll need more compute and that point is arguably right now...

### Thurs, July 7, 22
Market orders, limit orders, stop loss, take profit, time in force, if time in force is "GTD" need a cancel time. If limit order, need a price. If stop loss, take profit, need a price and direction and distance.

### Tues, May 10, 22
We should make a testing framework to validate design decisions such as "are limit orders better than market orders" and such.

To validate decisions like these we can assess the rate of drop-off of z-scores in the fore test accross a wide range of instruments and configuration settings (though that wouldn't cover limit vs market orders...)

Basically we need a way to search the configuration parameter space to find classes/sets/groups or configuration data that yields robust z-scores in fore testing. 

Z-score dropoff (overfitting) is the #1 enemy. Solve this => solve trading system => $$$. For the time being, all energy and attention spent on this trading system should focus on eliminating this enemy. The rest is details which can follow.

### Sun, May 1, 22
It's May!
To make crossover better or functional at all we should switch to a parameterized strindicator. We can do this using a code maybe? Each function type is encoded as a number... Crossover gets tricky because the strategy at the pinnacle of the strindicator only works well on its own inputs. Two strindicators can be both very good and very similar but unable to be crossovered simply because the inputs can be in different places. One could argue this doesn't matter because the GA will just pick the ones that work but this set up is potentially very inefficient. If we want to know whether it's actually inefficient we'd have to do some testing... blah. 

Still, a parameterized version would be cool. This could be a Neural Net or some type of parameterized (coded) version of what we already have. Although a parameterized version of what we already have would not be more efficient. The current setup just doesn't lend itself to productive reproduction via crossover. If we want something that lends itself to productive reproduction via crossover, that's a design constraint we need to include from the beginning which would necessitate a large (or complete) redesign. Keep thinking on this...

### Wed, Apr 13, 22
What's the best way to store hysts? Just put groups of them in the same files. The file names can be a sha256 hash of their stringified factory-config (or not stringified? whichever). Do we ever want to generate config from a hash? If so, we shouldn't use a one-way function like sha256... We'd have to use some type of encoding. We could just make our own code... just make a config->code function and a code->config function. The code can be a string to use as the file name. Or just use sha or some other hashing algorithm and make a lookup table in another file called "config.edn" or something. Just store the hash value with the config settings and voilà.

### Mon, Apr 11, 22
We should organize our hystrindies data better by splitting it into different files for different backtests. This will make it easier to work with for gausts too - which should also be split into different files (or added to the hyst files?)

Also, lets get the arena working.

### Fri, Apr 1, 22
The idea is to run a gauntlet with any hysty at all. Hysties have backtest config in them but we also need some way of telling what the future data is. Right now, we pull the data and use overlap index to tell what the future data is. This only works, however, if we have the old data, or know what it is somehow. We can put a timestamp in the hysty which could work but then we have to figure out from the new data how much of it is after that time stamp (not impossible). An alternative is to record open times for each open price in the stream data. This is a lot of extra data...

The problem is we're storing all the data to a file for easy access but there's no way of knowing, in the file, what times the prices are from. Somehow we need the times of prices in order to get the prices between the end of the hyst and the present. We need this to work for all "supported" time frames. 

Either way we need the time stamp in the hyst. That or just save the end however many values (like 10) of the first intention stream as a proxy to know our place.

### Thurs, Mar 31, 22
- Get rid of redundant data in saved edn files (multiple return streams in hystrindies.edn (really only need delta right?), multiple duplicate streams in streams.edn)

### Wed, Mar 30, 22
Todo:
- Long and short strategies (return -1, 0 or 1 instead of booleans)?
- Lots of instruments [x]
- Finish orders/trading system, tagging trades by strindy id

### Thurs, Mar 24, 22

Arena notes: How are we going to do the arena?
It's just like running a backtest. We solve the same strindy using the same solve-strindy function and simply pass in different inputs. The inputs will have come from the api and will be most recent (ie live). 

We will want to refactor the return streams of the hystrindies to include return deltas. The live trading strindy will produce new deltas. These new deltas will be compared to the backtest deltas via hypothesis test. The target threshold value of the hypothesis test (by which the decision to go live or not is derived) will be determined later. It's probably more performant to do everything based off deltas? Even inception streams?

Somewhere we'll have to run a chron job every x timeframe to get live prices with which to solve the strindy to get live return deltas. For now use the alienware desktop or aws lambda... We should start using the desktop soon though cause it's got better specs for running backtests.

Todo: Refactor return values of hystrindies to include deltas. 

### Fri, Mar 18, 22

How do we want to deal with strategy trees in strindy genetic algorithm? Seems like we'd want to optimize them... along with the indicators... and thus optimize the strindicator. Ok, good. How do we do that though? All we have in the strindicator is the actual solution function for the strategy tree. This is a wacko type of node.

Well, how do we update any branch? Change the function or change the inputs, that's all there is to change. In the strategy case, changing the function is just a little more involved than in the simple function types like addition and subtraction. 

There's another question of exactly how are we going to update the indicators. It's a little tricky because if there's a multi-input function with three inputs and then we trim one off... well the multi-input ones all work with two inputs, but if there's a one-input function and we add another input to it... it will either error out or just be a waste of a change...

We could/should add an amelioration function to the strindies which we could run the modified ones through and it could trim unused inputs and whatnot. In this way we could make all the strindy functions able to take n inputs and during amelioration the inputs get trimed back if necessary, just deleting random children until the function has the right number of inputs. We just need to be careful when adding/deleting children from a strategy tree node because there's an unacceptably high chance that will cause an error (if we don't also update the strategy tree accordingly).


### Sat, Feb 26, 22

Configuration stuff:
; Strindy config: by which strindies are created
; Strindy: the strindy tree itself (no inception/intention streams in itself, only stream ids).
; Backtested Strindy: package of - strindy, sieve stream and return stream(s), backtest data including (granularity & [num-data-points | (start-time, [end time])])
; Arena strindy: package of - backtested strindy, arena-performance {returns, z-score, other-score?}
; Live practice strindy: arena strindy + live-practive-performance {returns, z-score, other-score?}
;; (skip one of arena strindy, live practice strindy? or combine them rather?)
; Live trading strindy: live practice strindy + live-trading-performance {returns, z-score, other-score?}

### Thurs, Feb 24, 22

Is there any benefit of solving for return stream at each time step instead of calculating it after the whole sieve stream is generated? In the same vein, is it necessary / beneficial to calculate the whole input streams (both inception and intention streams) before solving for the sieve stream?

In real time (live) the sieve stream and return stream will be calculated at each time step so this capability is a must. If it's doing this in the live environment why do something different in the backtest environment? Well, it may be a performance increase to batch the calculation in backtesting, key word being "may". A performance comparison test would need to be run to verify this. Also, batching them is easier (maybe a little) conceptually. Though we'll have to write the live time-slice version anyways so the difficulty point is rather mute.

Just do it as they say. One time slice at a time.

This brings up another point that the inception streams should be subscribed to. Currently they're build in to the strindy solver function. Decouple this please and get instructions from config.

### Wed, Feb 23, 22

To confine strindicators to binary output one must use a binary function at the parent node. The greater than function is ideal for this. However, if one wants to compare more than two values to produce a binary result, one must use binary trees (decision trees). These are strategies in our system as it stands currently. Therefore, to constrain the output of our strindicators to binary, we must top off the strindicator with a binary tree. This is a new type of node.

We could also mix in binary tree nodes into the strindicator in lower layers. There are theoretically no problems with this though one could make the case that information is lost at these nodes.

It may prove beneficial to allow upper level nodes to subscribe to inputs of other nodes. This would make the strindicator tree into a strindcator graph or network. This is very similar to a neural network except nodes are allowed to have different activation functions. A neural net would be a subset of this type of strindicator which is fine. Then again, a graph is just a subset of a tree. Maybe make the strindicators trees for now with strategies potentially sprinkled in and turn it into a graph in the future for performance enhancement.

Get to arena asap. How else will we know whether we're actualy improving the system or not?

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

- [x] Make a recursive strindicator config generator. This will take in a set of inputs which each function in the strindicator function tree can subscribe to. To begin, use the integer series as the only input. After that, get it working with subscription inputs.
