# tiny_vm
A tiny virtual machine interpreter for Quack programs

## Work in progress

This is intended to become the core of an interpreter for the Winter 2022
offering of CIS 461/561 compiler construction course at University of Oregon, 
if I can ready it in time. 

## How to use

You might need to change the CMake config file to use cjson instead of cJSON
since I originally changed it to cJSON to make it work.

Also, use parser.py to transform from the arithmetic language into
assembly code. To read from a file or save to a file you must redirect
stdin and stdout to the files you want to use. parser.py should produce
assembly code that can be assembled by assemble.py.

A test file called test.quack is included in the unit_tests directory
if you want to use it to test the parser.
