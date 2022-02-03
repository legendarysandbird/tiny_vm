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

	typ: NAME

	assignment: typ ":" typ "=" rexp
		| typ ":" typ "=" methodcall

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

class Element:
	def __init__(self, typ, text):
		self.typ = typ
		self.text = text
	
	def __str__(self):
		return f"#Type: {self.typ} | Text: {self.text}#"

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
	
	def typ(self, name):
		return name

	def var(self, name):
		return name
	
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
		filename = sys.argv[1].split(".")[0]
		print(f".class {filename}:Obj\n.method $constructor")
		if len(var_list) > 0:
			print(".local ", end="")
			li = []
			for var in var_list:
				li.append(var)
			print(",".join(li))
		print("\tenter")
	
	def program(self, text1, text2):
		return f"{text1}{text2}"
	
	def statement(self, text):
		el = Element(text.typ, text.text)
		return text.text

	def assignment(self, name, typ, value):
		el = Element(value.typ, f"{value.text}\tstore {name.typ}\n")
		return el
		
	def var(self, name):
		el = Element(name.typ, f"\tload {name.typ}\n")
		return el
	
	def lexp(self, name):
		el = Element(name, "")
		return el
	
	def typ(self, name):
		el = Element(name, "")
		return el
	
	def rexp(self, value):
		el = Element(value.typ, value.text)
		return el
	
	def methodcall(self, value, method, arg=Element("String", "")):
		if value.typ in var_list:
			typ = var_list[value.typ]
		else:
			typ = value.typ

		roll = ""

		if method.typ == "sub" or method.typ == "div":
			roll = "\troll 1\n"

		el = Element(value.typ, f"{value.text}{arg.text}{roll}\tcall {typ}:{method.typ}\n")

		if method.typ == "print":
			el.text += "\tpop\n"

		return el			
	
	def string(self, text):
		el = Element("String", f"\tconst {text}\n")
		return el

	def add(self, a, b):
		el = Element(a.typ, f"{a.text}{b.text}\tcall {a.typ}:plus\n")
		return el

	def sub(self, a, b):
		el = Element(a.typ, f"{a.text}{b.text}\tcall {a.typ}:sub\n")
		return el

	def mul(self, a, b):
		el = Element(a.typ, f"{a.text}{b.text}\tcall {a.typ}:mult\n")
		return el

	def div(self, a, b):
		el = Element(a.typ, f"{a.text}{b.text}\tcall {a.typ}:div\n")
		return el

	def neg(self, a):
		el = Element(a.typ, f"\tconst 0\n{a.text}\tcall {a.typ}:sub\n")
		return el

	def number(self, num):
		el = Element("Int", f"\tconst {num} \n")
		return el

preprocessor = Lark(quack_grammar, parser='lalr', transformer=RewriteTree())
preprocessor = preprocessor.parse


def main():
	if len(sys.argv) != 2:
		print("Usage: python3 parser.py [name]")
		return

	with open(sys.argv[1]) as f:
		s = f.read()
	pre = preprocessor(s)
	tree = Lark(quack_grammar, parser='lalr', transformer=BuildTree())
	tree = tree.parse(pre)
	print(tree, end="")
	print("\tconst nothing")
	print("\treturn 0")

if __name__ == '__main__':
    main()
