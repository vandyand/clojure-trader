### Thu, Feb 17, 22

#### Using Straticators:

tree-config is the blueprint for creating decision-tree (binary) straticators
input-config contains blueprints for (continuous) straticators as inputs to (binary) straticators. In this sense, it's straticators all the way down (which is fine and dandy (literally)).
So, straticator config is everything that is necessary for building a straticator. Just put a key in there for return type which will define whether the straticator is a strategy or an indicator. This works right?
What do we need then, in order to build a straticator? We need the straticator function and the input stream(s). A sine wave straticator only needs the x-axis as input (once it's args are defined of course. You could say the args are inputs but meh, not loving. Just define the thing). It's args must be defined somewhere else in the config, namely in the function itself.

#### Straticator Schema

Straticator schema: {:fn function :inputs [...inputs]}. Recursive because inputs are potentially generated from other straticators.

The x-axis is assumed. For our purposes it is just the index of the input stream(s) which the function is currently evaluating (the instantanious inputs as it were) (which is just an incrementing integer series).

Therefore, to create a straticator, all one needs is the straticator config. Whether it's a strategy or an indicator can be determined by the function retun values. If the straticator function returns continuous values (besides simple binary) the straticator is defined as an indicator. If the straticator function returns only 0 or 1 (binary) it is either a strategy or an indicator.

#### Straticators are Recursive

inputs are streams. input streams are either subscription streams (streams such as instruments which are ingested from outside the system) or generated streams (streams which are generated from zero or more subscription streams). Generated streams are straticators. The definition of a straticator is recursive. Therefore we need to create some base straticators (or inputs rather... see below) from which all others may be derived (to avoid infinite recursion).

This also implies that straticator config is recursive.

Straticator functions can subscribe to previous values of input streams. The current value of an input stream and all previous values are fair game as instantanious inputs.

A straticator function is a recursive composition of other straticator functions.

The inputs are either the presumed index (x-axis) (incrementing integer series) or a subscribed data stream (array of {value at x index}) which is essentially a values (prices or whatever) stream where the index is the presumed x-axis (integer series') value.

For what it's worth, it has been shown that one can find fitting patterns (rising/profitable return streams) from intention streams (subscription streams) without using any subscription streams as input (that is, only using the x-axis and values generated from these using, say, random sine waves).

### Todo:

Make a recursive straticator config generator. This will take in a set of inputs which each function in the straticator function tree can subscribe to. To begin, use the integer series as the only input. After that, get it working with subscription inputs.
