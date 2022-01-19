from lark import Lark, Transformer, v_args

calc_grammar = """
	?start: sum
		| NAME: NAME "=" sum	-> assign_var

    ?sum: product
        | sum "+" product   	-> add
        | sum "-" product   	-> sub

    ?product: atom
        | product "*" atom  	-> mul
        | product "/" atom  	-> div

    ?atom: NUMBER           	-> number
         | "-" atom         	-> neg
		 | NAME					-> var
         | "(" sum ")"

    %import common.CNAME 		-> NAME
    %import common.NUMBER
    %import common.WS_INLINE

    %ignore WS_INLINE
"""


@v_args(inline=True)    # Affects the signatures of the methods
class CalculateTree(Transformer):
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

calc_parser = Lark(calc_grammar, parser='lalr', transformer=CalculateTree())
calc = calc_parser.parse


def main():
    while True:
        try:
            s = input()
        except EOFError:
            break
        print(calc(s))
    print("\tcall Int:print")
    print("\tpop")
    print('\tconst "\\n"')
    print("\tcall String:print")
    print("\tpop")
    print("\treturn 0")

if __name__ == '__main__':
    main()
