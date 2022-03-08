# compiler
A compiler for Quack programs.

## Work in progress

There are a lot of bugs with this compiler. my_tests has some programs that showcase working
features of the compiler. Theoretically, the compiler has some type checking, arithmetic, method
calls, class definitions, loops, if statements, and some more. The main things that are missing are
logical operators (and, or, not), some relational operators (only == and < are present), inheritance,
and typecase statements. Adding more relational operators would be pretty easy, and inheritance could
work, I'm just not quite sure what the assembly code should look like for inheritance to work in the
tiny_vm (the type system in the compiler is in place to make it work though). Typecases probably
wouldn't be too difficult either, I'd just need to pass a new type environment to the block of
the typecase. Logical operators are probably the most important thing I'm missing, which I just totally
forgot about them. However, despite missing some things, I've spent wayyyyy too long on this project
and just need to turn it in so I can go on with my life.

I think simpler programs should compile just fine, but more complex programs might fail to compile (you're
welcome to try your luck though). My test programs are probably the best indicator of what is possible.

## How to use

Run your Quack program like so: "./quack [filename]". This will delete any intermediate files that are
created in the building process (including the .json representation). If you want to keep the
intermediate files, run with the alternative script "./quackc [filename]".
