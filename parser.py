import sys
from lark import Lark, Transformer, v_args

quack_grammar = """
	?start: program

	?program: statement
		| program statement

	statement: rexp ";"
		| assignment ";"
		| methodcall ";"

	methodcall: rexp "." lexp "(" ")"
		| rexp "." lexp "(" atom ")"

	rexp: sum

	lexp: NAME

	assignment: lexp ":" typ "=" rexp
		| lexp ":" typ "=" methodcall

	typ: NAME

    ?sum: product
        | sum "+" product   	-> add
        | sum "-" product   	-> sub

    ?product: atom
        | product "*" atom  	-> mul
        | product "/" atom  	-> div

    ?atom: INT           		-> number
         | "-" atom         	-> neg
		 | lexp					-> var
         | "(" sum ")"			-> parens
		 | "(" methodcall ")"
		 | STRING               -> string

	%import common.CNAME 		-> NAME
	%import common.INT
    %import common.WS
	%import common.ESCAPED_STRING -> STRING

	%ignore WS
"""

var_list = {}

@v_args(inline=True)
class RewriteTree(Transformer):
	def program(self, text1, text2):
		return f"{text1}{text2}"

	def statement(self, text):
		return f"{text};\n"

	def assignment(self, name, typ, value):
		var_list[str(name)] = str(typ)
		return f"{name}: {typ} = {value}"

	def var(self, name):
		return name
	
	def typ(self, typ):
		return typ

	def lexp(self, name):
		return name
	
	def rexp(self, value):
		return value
	
	def methodcall(self, value, method, arg=""):
		return f"{value}.{method}({arg})"
	
	def string(self, text):
		return text

	def add(self, a, b):
		return f"{a}.plus({b})"

	def sub(self, a, b):
		return f"{a}.sub({b})"

	def mul(self, a, b):
		return f"{a}.mult({b})"

	def div(self, a, b):
		return f"{a}.div({b})"

	def neg(self, a):
		return f"0.sub({a})"

	def number(self, num):
		return num

	def parens(self, val):
		return f"({val})"

@v_args(inline=True)    # Affects the signatures of the methods
class BuildTree(Transformer):
	def __init__(self):
		print(".class Sample:Obj\n\n.method $constructor")
		print(".local ", end="")
		li = []
		for var in var_list:
			li.append(var)
		print(",".join(li))

	def program(self, text1, text2):
		return f"{text1}{text2}"
	
	def statement(self, text):
		return text

	def assignment(self, name, typ, value):
		#print(f"@ [{name}: ({typ}, {value})] @")

		ret = value
		ret += f"\tstore {name}\n"

		return ret
		

	def var(self, name):
		return f"\tload {name}\n"
	
	def typ(self, typ):
		return typ

	def lexp(self, name):
		return name
	
	def rexp(self, value):
		return value
	
	def methodcall(self, value, method, arg=""):
		#typ = var_list[value][0]
		val = value.split(" ")[-1]
		try:
			int(val)
			typ = "Int"
		except ValueError:
			if val in var_list:
				typ = var_list[val]
			else:
				typ = "String"
			
		ret = f"{value}{arg}"
		ret += f"\tcall {typ}:{method}\n"
		return ret
	
	def string(self, text):
		return f"\tconst {text}\n"

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

#parser = Lark(quack_grammar, parser='lalr', transformer=BuildTree())
#tree = parser.parse

preprocessor = Lark(quack_grammar, parser='lalr', transformer=RewriteTree())
preprocessor = preprocessor.parse


def main():
	s = sys.stdin.read()
	pre = preprocessor(s)
	tree = Lark(quack_grammar, parser='lalr', transformer=BuildTree())
	tree = tree.parse(pre)
	print(tree)

if __name__ == '__main__':
    main()
