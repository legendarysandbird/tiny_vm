import sys
from lark import Lark, Transformer, v_args, Tree, Token

quack_grammar = """
    ?start: program

    ?program: statement
        | program statement

    statement: rexp ";"
        | assignment ";"
        | methodcall ";"
        | loop
        | condif

    loop: "while" rexp "{" statement "}"

    condif: "if" rexp "{" statement "}" [condelif] [condelse]

    condelif: "elif" rexp "{" statement "}" [condelif]

    condelse: "else" "{" statement "}"

    methodcall: rexp "." lexp "(" ")"
        | rexp "." lexp "(" atom ")"

    rexp: sum

    lexp: NAME

    typ: NAME

    assignment: typ ":" typ "=" rexp
        | typ ":" typ "=" methodcall

    ?sum: product
        | sum "+" product       -> plus
        | sum "-" product       -> sub

    ?product: atom
        | product "*" atom      -> mult
        | product "/" atom      -> div

    ?atom: INT                  -> number
         | "-" atom             -> neg
         | lexp                 -> var
         | "(" sum ")"
         | "(" methodcall ")"
         | STRING               -> string

    %import common.CNAME        -> NAME
    %import common.INT
    %import common.WS
    %import common.ESCAPED_STRING -> STRING

    %ignore WS
"""

# Abstract Base Class

class ASTNode:
    def get_assembly(self):
        NotImplementedError(f"{self.__name} should have a get_assembly method")

class Program(ASTNode):
    def __init__(self, left, right):
        self.left = left
        self.right = right

    def get_assembly(self):
        left = self.left.get_assembly()
        right = self.right.get_assembly()
        return f"{left}{right}"

# Control Flow

class Conditional(ASTNode):
    def __init__(self, condition, block):
        self.condition = condition
        self.block = block

    def get_assembly(self):
        condition = self.condition.get_assembly()
        return f"{condition}\tjump_if block1\n\tjump {next_jump}{part2.text}{part3.text}end:\n"

# Arithmetic Operations

class BinOp(ASTNode):
    def __init__(self, op, left, right):
        self.op = op
        self.left = left
        self.right = right
        self.typ = "Int"

    def get_assembly(self):
        left = self.left.get_assembly()
        right = self.right.get_assembly()
        typ = self.typ
        op = self.op
        return f"{left}{right}\tcall {typ}:{op}\n"

class Negate(ASTNode):
    def __init__(self, val):
        self.val = val
        self.typ = "Int"

    def get_assembly(self):
        val = self.val.get_assembly()
        typ = self.typ
        el = Element(a.typ, f"\tconst 0\n{a.text}\tcall {a.typ}:sub\n")
        return f"\tconst 0\n{val}\tcall {typ}:sub\n"

class Methodcall(ASTNode):
    def __init__(self, val, method, args):
        self.typ = val.get_typ()
        self.method = method
        self.val = val
        self.args = args

    def get_assembly(self):
        typ = self.typ
        method = self.method
        val = self.val.get_assembly()
        arg = self.args
        if arg != "":
            arg = self.args.get_assembly()
        roll = ""

        if method == "sub" or method == "div":
            roll = "\troll 1\n"

        text = f"{val}{arg}{roll}\tcall {typ}:{method}\n"

        if method == "print":
            text += "\tpop\n"

        return text

    def get_typ(self):
        return self.typ

# Constants

class Const(ASTNode):
    def __init__(self, val):
        self.val = val

    def get_assembly(self):
        val = self.val
        return f"\tconst {val}\n"

    def get_typ(self):
        return self.typ

class Number(Const):
    def __init__(self, val):
        super().__init__(val)
        self.typ = "Int"

class String(Const):
    def __init__(self, val):
        super().__init__(val)
        self.typ = "String"

# Variables

class Var(ASTNode):
    def __init__(self, name, typ, val):
        self.name = name
        self.typ = typ
        self.val = val

    def set_typ(self, typ):
        self.typ = typ

    def set_val(self, val):
        self.val = val

    def get_assembly(self):
        name = self.name
        return f"\tload {name}\n"

    def get_typ(self):
        return self.typ

class Assignment(ASTNode):
    def __init__(self, name, typ, val):
        self.name = name
        self.typ = typ
        self.val = val
        var_list[self.name].set_typ(typ)
        var_list[self.name].set_val(val)
    
    def get_assembly(self):
        val = self.val.get_assembly()
        name = self.name
        return f"{val}\tstore {name}\n"

var_list = {}

@v_args(inline=True)
class RewriteTree(Transformer):
    def _arithmetic(self, a, b, name):
        return Tree(Token('Rule', 'methodcall'),
                    [Tree(Token('RULE', 'rexp'), [a]), #Left
                    Tree(Token('RULE', 'lexp'), [Token('NAME', name)]), #Right
                    b #Arg
                    ])

    def plus(self, a, b):
        return self._arithmetic(a, b, "plus")

    def sub(self, a, b):
        return self._arithmetic(a, b, "sub")

    def mult(self, a, b):
        return self._arithmetic(a, b, "mult")

    def div(self, a, b):
        return self._arithmetic(a, b, "div")

    def assignment(self, name, typ, value):
        var_list[str(name.children[0])] = Var(str(name.children[0]), str(typ.children[0]), str(value.children[0].children[0]))
        return Tree(Token('RULE', 'assignment'), [name, typ, value])

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
    
    def program(self, left, right):
        return Program(left, right)
    
    def statement(self, node):
        return node

    def lexp(self, name):
        return str(name)
    
    def typ(self, name):
        return str(name)

    def assignment(self, name, typ, val):
        return Assignment(name, typ, val)

    def var(self, name):
        return var_list[str(name)]
    
    def rexp(self, math_node):
        return math_node

    def number(self, val):
        return Number(val)

    def string(self, text):
        return String(text)

    def methodcall(self, val, method, args=""):
        return Methodcall(val, method, args)
    
'''
    def loop(self, condition, block):
        el = Element("String", f"\tjump end\nstart:\n{block}end:\n{condition.text}\tjump_if start\n")
        return el

    def condif(self, condition, block, part2 = Element("None", ""), part3 = Element("None", "")):
        next_jump = "end"

        if part2.typ != "None":
            next_jump = "block2"
        elif part3.typ != "None":
            next_jump = "block3" 

        el = Element("String", f"{condition.text}\tjump_if block1\n\tjump {next_jump}{part2.text}{part3.text}end:\n") 
        return el

    def condelif(self, condition, block, part2 = Element("None", "")):

        el = Element("String", f"{condition.text}\tjump_if block2\n\tjump block3{part3.text}\n")
        return el

    def condelse(self, block):
        el = Element("String", f"{block.text}")
        return el
'''

preprocessor = Lark(quack_grammar, parser='lalr', transformer=RewriteTree())
preprocessor = preprocessor.parse


def main():
    if len(sys.argv) != 2:
        print("Usage: python3 parser.py [name]")
        return

    with open(sys.argv[1]) as f:
        s = f.read()
    
    pre = preprocessor(s)
    tree = BuildTree().transform(pre)
    tree = tree.get_assembly()

    print(tree, end="")
    print("\tconst nothing")
    print("\treturn 0")

if __name__ == '__main__':
    main()
