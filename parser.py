import sys
from lark import Lark, Transformer, v_args, Tree, Token
from quackGrammar import quack_grammar
from Type import *

# Provide unique names to all labels

if_count = 0
elif_count = 0
elif_inner_count = 0
else_count = 0
while_count = 0

# Global

current_class = None
current_function = None

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

class Else(ASTNode):
    def __init__(self, block):
        super().__init__()
        self.block = block

    def get_assembly(self):
        global else_count
        block = self.block.get_assembly()
        
        return f"else{else_count}:\n{block}"

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

        return msg

# Arithmetic Operations

class BinOp(ASTNode):
    def __init__(self, op, left, right):
        super().__init__()
        self.op = op
        self.left = left
        self.right = right
        self.typ = types["Int"]

    def get_assembly(self):
        left = self.left.get_assembly()
        right = self.right.get_assembly()
        typ = self.typ
        op = self.op
        return f"{left}{right}\tcall {typ}:{op}\n"

class Negate(ASTNode):
    def __init__(self, val):
        super().__init__()
        self.val = val
        self.typ = types["Int"]

    def get_assembly(self):
        val = self.val.get_assembly()
        typ = self.typ
        el = Element(a.typ, f"\tconst 0\n{a.text}\tcall {a.typ}:sub\n")
        return f"\tconst 0\n{val}\tcall {typ}:sub\n"

class Methodcall(ASTNode):
    def __init__(self, val, method, args):
        super().__init__()
        self.typ = set()
        self.method = method
        self.val = val
        self.args = args
        

    def get_assembly(self):
        val = self.val
        method = self.method
        if len(val.get_typ()) > 0:
            for typ in val.get_typ():
                assert method in types[typ.name].methods, f"Type Checker: {typ} does not have a {method} method!"
                new_typ = types[types[typ.name].methods[method].ret]
                break
            self.typ.add(new_typ)

        typs = list(val.get_typ())
        typ = types["Int"]
        while len(typs) > 1:
            ancestor = typs[0].get_common_ancestor(typs[1])
            if len(typs) == 2:
                typs = [ancestor]
            else:
                typs = [ancestor] + typs[2:]

        if len(typs) > 0:
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
            text += "\tpop"

        return text

    def get_typ(self):
        return self.typ

class Function(ASTNode):
    def __init__(self, name, params, typ, program, ret):
        super().__init__()
        self.name = name
        self.params = params
        self.typ = typ
        self.program = program
        self.ret = ret

    def get_assembly(self):
        params = {}
        for param in self.params:
            params[param[0]] = param[1]

        types[current_class].methods[self.name] = Method(self.name, self.typ, params)

        program = ""
        for line in program:
            program += line.get_assembly()

        ret = self.ret.get_assembly()
        if type(self.ret) == Field:
            ret = "load $\n\tload_field " + ret

        text = f".method {self.name}\n\tenter\n{program}\t{ret}\treturn {len(self.params)}"
        return text

class Field(ASTNode):
    def __init__(self, val, field):
        super().__init__()
        if val == "this":
            val = "$"
        self.val = val
        self.field = field

    def get_assembly(self):
        typ = types[current_class].props[self.field]

        if self.val == "$":
            types[current_class].props[str(self.field)] = typ

        return f"{self.val}:{self.field}\n"

    def fill_typs(self, env):
        self.typs = env[self.field].typs

    def get_typ(self):
        typs = self.typs
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

class Class(ASTNode):
    def __init__(self, name, params, parent, code, funcs):
        super().__init__()
        self.name = name
        self.params = params
        self.parent = parent 
        self.code = code
        self.funcs = funcs

        types[self.name] = Type(self.name, parent, [], {}, {})

        for param in self.params:
            s = set()
            s.add(types[self.params[param]])
            types[self.name].props[param] = Var(param, s, param)
            types[self.name].props[param].set_valid()

        for piece in self.code:
            if type(piece) == Assignment:
                piece.fill_typs(types[self.name].props)

        parent = types[self.parent]

        var_list[self.name] = {}

        for local in params:
            var_list[self.name][local] = Var(local, params[local], "Unknown")

    def __str__(self):
        return f"Class: {self.name}"

    def get_assembly(self):
        global current_class
        current_class = self.name

        name = self.name
        parent = self.parent

        code = ".method $constructor\n"

        if len(self.params) > 0:
            code += ".args "
            li = []
            for param in self.params:
                li.append(param)
            code += ",".join(li) + "\n"

        code += "\tenter\n"

        for line in self.code:
            code += line.get_assembly()

        funcs = ""
        for func in self.funcs:
            if func != 'print':
                funcs += self.funcs[func].get_assembly()

        fields = ""
        for key in types[current_class].props:
            fields += f".field {key}\n"

        with open(f"{self.name}.asm", "w") as fil:
            fil.write(f".class {name}:{parent}\n{fields}{code}\tload $\n\treturn {len(self.params)}\n\n{funcs}")
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

        return f"{ret}\tnew {name}\n\tcall {name}:$constructor\n"

    def get_typ(self):
        s = set()
        s.add(types[self.name])
        return s


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

class Number(Const):
    def __init__(self, val):
        super().__init__(val)
        self.typ = set()
        typ = types["Int"]
        self.typ.add(typ)

class String(Const):
    def __init__(self, val):
        super().__init__(val)
        self.typ = set()
        typ = types["String"]
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

class Assignment(ASTNode):
    def __init__(self, name, val):
        super().__init__()
        self.name = name
        self.val = val
        self.typ = "Unknown"

    def get_assembly(self):
        val = self.val.get_assembly()
        name = self.name.get_assembly()
        store = "store"

        if type(self.name) == Field:
            store = "load $\n\tstore_field"
        return f"{val}\t{store} {name}"

    def fill_typs(self, env):
        self.typ = env[self.val].typs
        self.val = env[self.val]

        if type(self.name) == Field:
            self.name.fill_typs(env)


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

@v_args(inline=True)    # Affects the signatures of the methods
class BuildTree(Transformer):
    def __init__(self):
        """
        filename = sys.argv[1].split("/")[-1].split(".")[-2]
        print(f".class {filename}:Obj\n.method $constructor")
        if len(var_list) > 0:
            print(".local ", end="")
            li = []
            for var in var_list:
                li.append(var)
            print(",".join(li))
        print("\tenter", end="")
        """
        pass
    
    def program(self, left, right):
        return Program(left, right)
    
    def statement(self, node):
        return node

    def field(self, parent, name):
        return Field(parent, name)
    
    def typ(self, name):
        return str(name)

    def typed(self, name, typ, val):
        return Assignment(name, val)

    def untyped(self, name, val):
        return Assignment(name, val)

    def var(self, name):
        return str(name)
    
    def rexp(self, math_node):
        return math_node

    def number(self, val):
        return Number(val)

    def string(self, text):
        return String(text)

    def methodcall(self, val, method, args=""):
        return Methodcall(val, method, args)

    def field(self, val, field):
        return Field(val, str(field))
    
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
        li = {} 
        for func in funcs:
            li.update({func.name: func})
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

    filename = sys.argv[1].split("/")[-1].split(".")[-2]

    output = f".class {filename}:Obj\n.method $constructor\n"
    if len(var_list) > 0:
        output += ".local "
        li = []
        for var in var_list:
            li.append(var)
        output += ",".join(li)
    output += "\tenter\n"

    pre = preprocessor(s)
    tree = BuildTree().transform(pre)
    output += tree.get_assembly()
    output += "\n\tconst nothing\n\treturn 0"

    with open(filename + ".asm", "w") as f:
        f.write(output)

if __name__ == '__main__':
    main()
