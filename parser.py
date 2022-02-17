import sys
from lark import Lark, Transformer, v_args, Tree, Token

quack_grammar = """
    ?start: program

    ?program: statement
        | program statement

    statement: rexp ";"
        | assignment ";"
        | methodcall ";"
        | loop ";"
        | condif ";"

    loop: "while" "(" rexp ")" "{" program "}"

    condif: "if" rexp "{" statement "}" [condelif] [condelse]

    condelif: "elif" rexp "{" statement "}" [condelif]

    condelse: "else" "{" statement "}"

    methodcall: rexp "." lexp "(" ")"
        | rexp "." lexp "(" atom ")"

    rexp: sum

    lexp: NAME

    typ: NAME

    ?assignment: typed
        | untyped

    typed: typ ":" typ "=" rexp
        | typ ":" typ "=" methodcall

    untyped: typ "=" rexp
        | typ "=" methodcall

    ?sum: product
        | sum "+" product       -> plus
        | sum "-" product       -> sub

    ?product: relation
        | product "*" relation  -> mult
        | product "/" relation  -> div

    ?relation: atom
        | relation "<" atom     -> lt
        | relation "==" atom    -> eq

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

# Provide unique names to all labels

if_count = 0
elif_count = 0
elif_inner_count = 0
else_count = 0
while_count = 0

# Methods
methods = {
        "Int": {"plus": "Int", "sub": "Int", "mult": "Int", "div": "Int", "less": "Boolean", "equals": "Boolean", "print": "Nothing", "string": "String"},
        "String": {"string": "String", "print": "Nothing", "equals": "Boolean", "less": "Boolean", "plus": "String"},
        "Obj": {"string": "String", "print": "Nothing", "equals": "Boolean"}
        }

# Possible types

class Type:
    def __init__(self, name, parent, children):
        self.name = name
        self.parent = parent
        self.children = children

    def __str__(self):
        return f"{self.name.upper()}"

    def __repr__(self):
        return f"Type({self.name}, {self.parent}, {self.children})"

    def get_common_ancestor(self, other):
        type1 = self
        type2 = other
        while type1.name != type2.name:
            if type1.name == "Obj" and type2.name == "Obj":
                break
            elif type2.name == "Obj":
                type1 = type1.parent
                type2 = other
            else:
                type2 = type2.parent

        return type1

Obj = Type("Obj", None, ["Int", "String"])
String = Type("String", Obj, [])
Int = Type("Int", Obj, [])
types = [
        Obj,
        String,
        Int
        ]


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

class If(ASTNode):
    def __init__(self, condition, block, elif_node, else_node):
        self.condition = condition
        self.block = block
        self.elif_node = elif_node
        self.else_node = else_node

    def get_assembly(self):
        global if_count, elif_count, elif_inner_count, else_count
        condition = self.condition.get_assembly()
        block = self.block.get_assembly()
        next_label = f"if_end{if_count}"

        elif_asm = ""
        else_asm = ""

        if self.else_node is not None:
            else_asm = self.else_node.get_assembly()
            next_label = f"else{else_count}"

        if self.elif_node is not None:
            elif_asm = self.elif_node.get_assembly(next_label, next_label)
            next_label = f"elif{elif_count}v{elif_inner_count - 1}"

        msg = f"{condition}\tjump_ifnot {next_label}\n{block}\tjump if_end{if_count}\n{elif_asm}{else_asm}if_end{if_count}:\n"
        if_count += 1
        elif_count += 1
        else_count += 1
        elif_inner_count = 0
        
        return msg

class Elif(ASTNode):
    def __init__(self, condition, block, elif_node):
        self.condition = condition
        self.block = block
        self.elif_node = elif_node

    def get_assembly(self, next_label, final_label):
        global elif_count, elif_inner_count

        condition = self.condition.get_assembly()
        block = self.block.get_assembly()
        
        elif_asm = ""
 
        if self.elif_node is None:
            next_label = final_label
        else:
            next_label = f"elif{elif_count}v{elif_inner_count}"
            elif_asm = self.elif_node.get_assembly(next_label, final_label)

        msg = f"elif{elif_count}v{elif_inner_count}:\n{condition}\tjump_ifnot {next_label}\n{block}\tjump if_end{if_count}\n{elif_asm}"
        elif_inner_count += 1
        return msg
        

class Else(ASTNode):
    def __init__(self, block):
        self.block = block

    def get_assembly(self):
        global else_count
        block = self.block.get_assembly()
        
        return f"else{else_count}:\n{block}"

class Loop(ASTNode):
    def __init__(self, condition, block):
        self.condition = condition
        self.block = block

    def get_assembly(self):
        global while_count

        condition = self.condition.get_assembly()
        block = self.block.get_assembly()

        msg = f"\tjump while_end{while_count}\nwhile_start{while_count}:\n{block}while_end{while_count}:\n{condition}\tjump_if while_start{while_count}\n"
        while_count += 1

        return msg

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
        self.typ = set()
        for typ in val.get_typ():
            assert method in methods[typ.name], f"Type Checker: {typ} does not have a {method} method!"
            new_typ = methods[typ.name][method]
            break
        for typ in types:
            if new_typ == typ.name:
                self.typ.add(typ)
        self.method = method
        self.val = val
        self.args = args
        

    def get_assembly(self):
        typs = list(self.val.get_typ())
        typ = "Unknown"
        while len(typs) > 1:
            ancestor = typs[0].get_common_ancestor(typs[1])
            if len(typs) == 2:
                typs = [ancestor]
            else:
                typs = [ancestor] + typs[2:]

        typ = typs[0]

        method = self.method
        val = self.val.get_assembly()
        arg = self.args
        if arg != "":
            arg = self.args.get_assembly()
        roll = ""

        if method == "sub" or method == "div" or method == "less":
            roll = "\troll 1\n"

        text = f"{val}{arg}{roll}\tcall {typ.name}:{method}\n"

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
        self.typ = set()
        for typ in types:
            if typ.name == "Int":
                self.typ.add(typ)

class String(Const):
    def __init__(self, val):
        super().__init__(val)
        self.typ = set()
        for typ in types:
            if typ.name == "String":
                self.typ.add(typ)

# Variables

class Var(ASTNode):
    def __init__(self, name, typ, val):
        self.name = name
        self.typs = typ
        self.val = val

    def set_typ(self, typ):
        self.typs = self.typs.union(typ)

    def set_val(self, val):
        self.val = val

    def get_assembly(self):
        name = self.name
        return f"\tload {name}\n"

    def get_typ(self):
        return self.typs

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

    def eq(self, a, b):
        return self._arithmetic(a, b, "equals")

    def lt(self, a, b):
        return self._arithmetic(a, b, "less")

    def typed(self, name, typ, value):
        for cur_typ in types:
            if cur_typ.name == str(typ.children[0]):
                typ = cur_typ
                break

        cur_types = set()
        cur_types.add(typ)

        if str(name.children[0]) not in var_list:
            var_list[str(name.children[0])] = Var(str(name.children[0]), cur_types, str(value.children[0].children[0]))
        else:
            var_list[str(name.children[0])].typ.add(typ)
        return Tree(Token('RULE', 'typed'), [name, typ, value])
    
    def untyped(self, name, value):
        var_list[str(name.children[0])] = Var(str(name.children[0]), set(), str(value.children[0].children[0]))
        return Tree(Token('RULE', 'untyped'), [name, value])

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

    def typed(self, name, typ, val):
        typs = set()
        typs.add(typ)
        return Assignment(name, typs, val)

    def untyped(self, name, val):
        typ = val.get_typ()
        for cur_typ in types:
            if cur_typ.name == typ:
                typ = cur_typ
                break

        var_list[name].set_typ(typ)
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
    
    def loop(self, condition, block):
        return Loop(condition, block)

    def condif(self, condition, block, elif_node=None, else_node=None):
        return If(condition, block, elif_node, else_node)

    def condelif(self, condition, block, elif_node=None):
        return Elif(condition, block, elif_node)

    def condelse(self, block):
        return Else(block)

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
