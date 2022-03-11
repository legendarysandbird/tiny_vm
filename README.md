# compiler
A compiler for Quack programs.

## Work in progress

First off, this compiler is definitely a little bit buggy. Very complex programs probably won't compile,
so make sure to look at my test programs in the "my_tests" directory to see what is definitely working.
As of right now, the only things that aren't working at all in this compiler are inheritance and
typecase statements. I have the type system in place to implement inheritance, the only problem is that
I'm not sure what the assembly code is supposed to look like for it. And typecases probably wouldn't
be too hard to implement, I would just have to pass an updated environment into the typecase block.

## How to use

Run your Quack program like so: "./quack [filename]". This will delete any intermediate files that are
created in the building process (including the .json representation). If you want to keep the
intermediate files, run with the alternative script "./quackc [filename]".
