import sys
from lark import Lark, Transformer, v_args, Tree, Token

quack_grammar = r"""
    ?start: program

    ?program: statement
        | program statement

    statement: rexp ";"
        | assignment ";"
        | loop
        | condif
        | clazz

    clazz: "class" class_name "(" params ")" class_typ "{" block funcs "}"

    class_name: NAME

    class_typ: ["extends" NAME]             -> parent

    ?params: [param [("," params)]]

    param: NAME ":" typ

    ?args: [arg [("," args)]]

    arg: rexp

    funcs: func*

    func: "def" lexp "(" params ")" ":" typ "{" [block] "return" rexp ";" "}"

    block: statement* 

    loop: "while" "(" rexp ")" "{" program "}"

    condif: "if" rexp "{" program "}" [condelif] [condelse]

    condelif: "elif" rexp "{" program "}" [condelif]

    condelse: "else" "{" program "}"

    methodcall: lexp "." NAME "(" ")"
        | lexp "." NAME "(" atom ")"
        | quark "." NAME "(" ")"
        | quark "." NAME "(" atom ")"

    class_create: NAME "(" args ")"

    rexp: sum

    ?lexp: NAME                 -> var
        | lexp "." NAME         -> field

    typ: NAME

    ?assignment: lexp ":" typ "=" rexp    -> typed
        | lexp "=" rexp             -> untyped

    ?relation: sum
        | relation "<" sum     -> lt
        | relation "==" sum    -> eq

    ?sum: product
        | sum "+" product       -> plus
        | sum "-" product       -> sub

    ?product: atom
        | product "*" atom  -> mult
        | product "/" atom  -> div

    ?atom: methodcall
        | class_create
        | quark

    ?quark: INT                  -> number
        | "-" quark             -> neg
        | lexp
        | "(" sum ")"
        | STRING               -> string
        | bool

    ?bool: "true"                -> true
        | "false"               -> false

    COMMENT: "/*" /(.|\n)*/ "*/"

    %import common.CNAME        -> NAME
    %import common.INT
    %import common.WS
    %import common.ESCAPED_STRING -> STRING

    %ignore WS
    %ignore COMMENT
"""

# Provide unique names to all labels

if_count = 0
elif_count = 0
elif_inner_count = 0
else_count = 0
while_count = 0

# Methods
props = {
        "Int": {"plus": "Int", "sub": "Int", "mult": "Int", "div": "Int", "less": "Boolean", "equals": "Boolean", "print": "Nothing", "string": "String"},
        "String": {"string": "String", "print": "Nothing", "equals": "Boolean", "less": "Boolean", "plus": "String"},
        "Obj": {"string": "String", "print": "Nothing", "equals": "Boolean"},
        "Boolean": {"string": "String", "print": "Nothing", "equals": "Boolean"}
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

def get_typ_by_name(name):
    for typ in types:
        if typ.name == name:
            return typ

Obj = Type("Obj", None, ["Int", "String"])
String = Type("String", Obj, [])
Int = Type("Int", Obj, [])

types = [
        Obj,
        String,
        Int
        ]

# Abstract Base Class

node_list = []
var_list = {}

class ASTNode:
    def __init__(self):
        node_list.append(self)

    def get_assembly(self):
        NotImplementedError(f"{self.__name} should have a get_assembly method")

class Program(ASTNode):
    def __init__(self, left, right):
        super().__init__()
        self.left = left
        self.right = right

    def get_assembly(self):
        left = self.left.get_assembly()
        right = self.right.get_assembly()
        return f"{left}{right}"

    def update_typs(self):
        left = self.left.update_typs()
        right = self.right.update_typs()
        return left or right

# Control Flow

class If(ASTNode):
    def __init__(self, condition, block, elif_node, else_node):
        super().__init__()
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

    def update_typs(self):
        cond = self.condition.update_typs()
        block = self.block.update_typs()
        if self.elif_node is not None:
            elf = self.elif_node.update_typs()
        elif self.else_node is not None:
            els = self.else_node.update_typs()

        if cond:
            return cond
        elif block:
            return block
        elif elf:
            return elf
        elif els:
            return els

class Elif(ASTNode):
    def __init__(self, condition, block, elif_node):
        super().__init__()
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

    def update_typs(self):
        cond = self.condition.update_typs()
        block = self.block.update_typs()
        if self.elif_node is not None:
            elf = self.elif_node.update_typs()

        if cond:
            return cond
        elif block:
            return block
        elif elf:
            return elf

class Else(ASTNode):
    def __init__(self, block):
        super().__init__()
        self.block = block

    def get_assembly(self):
        global else_count
        block = self.block.get_assembly()
        
        return f"else{else_count}:\n{block}"

    def update_typs(self):
        return self.block.update_typs()

class Loop(ASTNode):
    def __init__(self, condition, block):
        super().__init__()
        self.condition = condition
        self.block = block

    def get_assembly(self):
        global while_count

        condition = self.condition.get_assembly()
        block = self.block.get_assembly()

        msg = f"\tjump while_end{while_count}\nwhile_start{while_count}:\n{block}while_end{while_count}:\n{condition}\tjump_if while_start{while_count}\n"
        while_count += 1

        self.update_typs()

        return msg

    def update_typs(self):
        cont = self.block.update_typs()
        while cont:
            self.block.update_typs() 

# Arithmetic Operations

class BinOp(ASTNode):
    def __init__(self, op, left, right):
        super().__init__()
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

    def update_typs(self):
        left = self.left.update_typs()
        right = self.right.update_typs()
        return left or right

class Negate(ASTNode):
    def __init__(self, val):
        super().__init__()
        self.val = val
        self.typ = "Int"

    def get_assembly(self):
        val = self.val.get_assembly()
        typ = self.typ
        el = Element(a.typ, f"\tconst 0\n{a.text}\tcall {a.typ}:sub\n")
        return f"\tconst 0\n{val}\tcall {typ}:sub\n"

    def update_typs(self):
        return self.val.update_typs()

class Methodcall(ASTNode):
    def __init__(self, val, method, args):
        super().__init__()
        self.typ = set()
        if len(val.get_typ()) > 0:
            for typ in val.get_typ():
                assert method in props[typ.name], f"Type Checker: {typ} does not have a {method} method!"
                new_typ = props[typ.name][method]
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

    def update_typs(self):
        orig_typ = self.typ
        changed = False

        for typ in self.typ:
            assert self.method in props[typ], f"Type Checker: [while loop] {self.typ} does not have a {self.method} method!"
            new = props[typ.name][method]
            for typ in types:
                if new == typ.name:
                    self.typ = typ
                    changed = True

        return changed

class Function(ASTNode):
    def __init__(self, name, params, typ, program, ret):
        super().__init__()
        self.name = name
        self.params = params
        self.typ = typ
        self.program = program
        self.ret = ret

class Field(ASTNode):
    def __init__(self, val, field):
        super().__init__()
        self.val = val
        self.field = field

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

        return f"\tload_field {typ.name}:{self.field}\n"

    def get_typ(self):
        typs = list(self.val.get_typ())
        typ = "Unknown"
        while len(typs) > 1:
            ancestor = typs[0].get_common_ancestor(typs[1])
            if len(typs) == 2:
                typs = [ancestor]
            else:
                typs = [ancestor] + typs[2:]

        typ = typs[0]

        assert self.field in props[typ.name], f"'{typ.name}' has no property '{self.field}'!"
        
        return props[typ.name][self.field].name

    def update_typs(self):
        return self.field.update_typs(self)

class Class(ASTNode):
    def __init__(self, name, params, parent, code, funcs):
        super().__init__()
        self.name = name
        self.params = params
        self.parent = parent 
        self.code = code
        self.funcs = funcs

        var_list[self.name] = {}

        for local in params:
            var_list[self.name][local] = Var(local, params[local], "Unknown")



    def __str__(self):
        return f"Class: {self.name}"

    def get_assembly(self):
        name = self.name
        parent = self.parent

        code = ""

        if len(self.params) > 0:
            code += ".method $constructor\n.args "
            li = []
            for param in self.params:
                li.append(param)
            code += ",".join(li) + "\n"

        code += "\tenter\n"

        for line in self.code:
            code += line.get_assembly()

        funcs = ""
        for func in self.funcs:
            funcs += func.get_assembly()

        with open(f"{self.name}.asm", "w") as fil:
            fil.write(f".class {name}:{parent}\n{code}{funcs}\tconst nothing\n\treturn 0")
        return ""

class Instance(ASTNode):
    def __init__(self, name, args):
        super().__init__()
        self.name = name
        self.args = args

    def get_assembly(self):
        name = self.name
        args = self.args

        ret = ""
        for arg in self.args:
            ret += arg.get_assembly()

        return f"{ret}\tnew {name}\n\tcall {name}:$constructor"


# Constants

class Const(ASTNode):
    def __init__(self, val):
        super().__init__()
        self.val = val

    def get_assembly(self):
        val = self.val
        return f"\tconst {val}\n"

    def get_typ(self):
        return self.typ

    def update_typs(self):
        return False

class Number(Const):
    def __init__(self, val):
        super().__init__(val)
        self.typ = set()
        typ = get_typ_by_name("Int")
        self.typ.add(typ)

class String(Const):
    def __init__(self, val):
        super().__init__(val)
        self.typ = set()
        typ = get_typ_by_name("String")
        self.typ.add(typ)

class Bool(Const):
    def __init__(self, val):
        super().__init__()
        super().__init__(val)
        self.typ = set()
        for typ in types:
            if typ.name == "Boolean":
                self.typ.add(typ)

# Variables

class Var(ASTNode):
    def __init__(self, name, typ, val):
        super().__init__()
        self.name = name
        self.typs = typ
        self.val = val
        self.valid = False

    def set_typ(self, typ):
        self.typs = self.typs.union(typ)

    def set_val(self, val):
        self.val = val

    def set_valid(self):
        self.valid = True

    def get_assembly(self):
        assert self.valid, f"Variable {self.name} has not been initialized before use"
        name = self.name
        return f"\tload {name}\n"

    def get_typ(self):
        return self.typs

    def update_typs(self):
        return False

class Assignment(ASTNode):
    def __init__(self, name, val):
        super().__init__()
        self.name = name
        self.val = val
        self.typ = "Unknown"

    def get_assembly(self):
        var_list[self.name].set_valid()
        self.fill_typs()

        val = self.val.get_assembly()
        name = self.name
        return f"{val}\tstore {name}\n"

    def update_typs(self):
        return False

    def fill_typs(self):
        self.typ = self.val.get_typ()
        typ = self.typ
        val = self.val

        #self.vars[self.name].set_typ(typ)
        #self.vars[self.name].set_val(val)


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

    '''
    def typed(self, name, typ, value):
        typ = get_typ_by_name(str(typ.children[0]))

        cur_types = set()
        cur_types.add(typ)

        if str(name.children[0]) not in var_list:
            self.vars[str(name.children[0])] = Var(str(name.children[0]), cur_types, str(value.children[0].children[0]))
        else:
            self.vars[str(name.children[0])].typ.add(typ)

        return Tree(Token('RULE', 'typed'), [name, typ, value])
    
    def untyped(self, name, value):
        self.vars[str(name.children[0])] = Var(str(name.children[0]), set(), str(value.children[0].children[0]))

        return Tree(Token('RULE', 'untyped'), [name, value])
    '''


@v_args(inline=True)    # Affects the signatures of the methods
class BuildTree(Transformer):
    def __init__(self):
        filename = sys.argv[1].split("/")[-1].split(".")[-2]
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

    def field(self, parent, name):
        return Field(parent, name)
    
    def typ(self, name):
        return str(name)

    def typed(self, name, typ, val):
        return Assignment(name, val)

    def untyped(self, name, val):
        return Assignment(name, val)

    def var(self, name):
        return name
    
    def rexp(self, math_node):
        return math_node

    def number(self, val):
        return Number(val)

    def string(self, text):
        return String(text)

    def methodcall(self, val, method, args=""):
        return Methodcall(val, method, args)

    def field(self, val, field):
        return Field(val, field)
    
    def loop(self, condition, block):
        return Loop(condition, block)

    def condif(self, condition, block, elif_node=None, else_node=None):
        return If(condition, block, elif_node, else_node)

    def condelif(self, condition, block, elif_node=None):
        return Elif(condition, block, elif_node)

    def condelse(self, block):
        return Else(block)

    def true(self):
        return Bool("true")

    def false(self):
        return Bool("false")

    def clazz(self, name, params, parent, code, funcs):
        cl = Class(name, params, parent, code, funcs)
        return cl

    def class_name(self, name):
        return str(name)

    def parent(self, name=None):
        if not name:
            name = "Obj"

        return name

    def params(self, *params):
        typs = {}
        for arg in params:
            if arg is not None:
                typs.update(arg)

        return typs

    def param(self, name, typ):
        parm = {str(name): str(typ)}
        return parm

    def args(self, *args):
        vals = []
        for arg in args:
            if arg is not None:
                vals += arg

        return vals

    def arg(self, val):
        arg = [val]
        return arg

    def class_create(self, name, args):
        ins = Instance(name, args)
        return ins

    def block(self, *programs):
        li = []
        for program in programs:
            li.append(program)
        return li

    def funcs(self, *funcs):
        li = []
        for func in funcs:
            li.append(func)
        return li

    def func(self, name, params, typ, program, ret):
        func = Function(name, params, typ, program, ret)
        return func


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
    output = tree.get_assembly()
    print(output)
    print("\tconst nothing\n\treturn 0")

if __name__ == '__main__':
    main()
