import sys
from lark import Lark, Transformer, v_args

quack_grammar = """
	?start: program

	program: statement
		| program statement

	statement: rexp ";"
		| assignment ";"
		| methodcall ";"

	methodcall: rexp "." NAME "(" ")"

	rexp: sum

	lexp: NAME

	assignment: lexp ":" type "=" rexp

	type: NAME

    ?sum: product
        | sum "+" product   	-> add
        | sum "-" product   	-> sub

    ?product: atom
        | product "*" atom  	-> mul
        | product "/" atom  	-> div

    ?atom: NUMBER           	-> number
         | "-" atom         	-> neg
		 | lexp					-> var
         | "(" sum ")"

	%import common.CNAME 		-> NAME
	%import common.NUMBER
    %import common.WS

	%ignore WS
"""


@v_args(inline=True)    # Affects the signatures of the methods
class BuildTree(Transformer):
    def __init__(self):
        print(".class Sample:Obj")
        print()
        print(".method $constructor")

    def add(self, a, b):
        ret = a + b
        ret += "\tcall Int:plus\n"

        return ret

    def sub(self, a, b):
        ret = a + b
        ret += "\tcall Int:sub\n"

        return ret

    def mul(self, a, b):
        ret = a + b
        ret += "\tcall Int:mult\n"

        return ret

    def div(self, a, b):
        ret = a + b
        ret += "\tcall Int:div\n"

        return ret

    def neg(self, a):
        ret = "\tconst 0\n"
        ret += a
        ret += "\tcall Int:sub\n"

        return ret

    def number(self, num):
        return "\tconst " + str(num) + "\n"

parser = Lark(quack_grammar, parser='lalr')
tree = parser.parse


def main():
	s = sys.stdin.read()
	print()
	print(tree(s).pretty())

if __name__ == '__main__':
    main()
