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

current_class = "Global"
current_function = "Constr"

# Abstract Base Class

node_list = []
var_list = {"Global": {"Constr": {}}}
file_list = []

class ASTNode:
    def __init__(self):
        node_list.append(self)

    def get_assembly(self):
        NotImplementedError(f"{self.__name} should have a get_assembly method")

    def update_info(self):
        NotImplementedError(f"{self.__name} should have an update_info method")


class Program(ASTNode):
    def __init__(self, left, right):
        super().__init__()
        self.left = left
        self.right = right

    def get_assembly(self):
        left = self.left.get_assembly()
        right = self.right.get_assembly()
        return f"{left}{right}"

    def update_info(self):
        self.left.update_info()
        self.right.update_info()

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

    def update_info(self):
        self.condition.update_info()
        self.block.update_info()
        if self.elif_node is not None:
            self.elif_node.update_info()
        if self.else_node is not None:
            self.else_node.update_info()

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

    def update_info(self):
        self.condition.update_info()
        self.block.update_info()
        if self.elif_node is not None:
            self.elif_node.update_info()

class Else(ASTNode):
    def __init__(self, block):
        super().__init__()
        self.block = block

    def get_assembly(self):
        global else_count
        block = self.block.get_assembly()
        
        return f"else{else_count}:\n{block}"

    def update_info(self):
        self.block.update_info()

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

    def update_info(self):
        self.condition.update_info()
        self.block.update_info()

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
        return f"{left}{right}\tcall {self.typ}:{self.op}\n"

    def update_info(self):
        self.op.update_info()
        self.left.update_info()
        self.right.update_info()

class Negate(ASTNode):
    def __init__(self, val):
        super().__init__()
        self.val = val
        self.typ = types["Int"]

    def get_assembly(self):
        val = self.val.get_assembly()
        return f"\tconst 0\n{val}\tcall {self.typ}:sub\n"

    def update_info(self):
        self.val.update_info()

class Methodcall(ASTNode):
    def __init__(self, val, method, args):
        super().__init__()
        self.method = method
        self.val = val
        self.args = args
        self.typ = "Unknown"
        
    def get_assembly(self):
        val = self.val.get_assembly()

        arg = ""
        for argu in self.args:
            if type(argu) == str:
                index = argu.find(".")
                if index == -1:
                    argu = var_list[current_class][current_function][argu]
                else:
                    name = argu.split(".")
                    typ = var_list[current_class][current_function][name[0]].get_typ().name
                    if typ == current_class:
                        typ = "$"
                    argu = Field(name[0], name[1], typ)
                    argu.valid = True
            arg += argu.get_assembly()

        roll = ""

        if self.method == "sub" or self.method == "div" or self.method == "less" or self.method == "plus":
            roll = "\troll 1\n"

        text = f"{val}{arg}{roll}\tcall {self.typ.name}:{self.method}\n"

        if self.method == "print":
            text += "\tpop\n"

        return text

    def update_info(self):
        if type(self.val) == str:
            index = self.val.find(".")
            if index == -1:
                self.val = var_list[current_class][current_function][self.val]
            else:
                name = self.val.split(".")
                if name[0] == "$" or name[0] == "this":
                    self.val = var_list[current_class][name[1]]
                else:
                    self.val = var_list[name[0]][name[1]]
        self.val.update_info()
        self.typ = self.val.get_typ()
        for arg in self.args:
            if type(arg) == str:
                index = arg.find(".")
                if index == -1:
                    arg = var_list[current_class][current_function][arg]
                else:
                    name = arg.split(".")
                    arg = var_list[current_class][current_function][name[0]]
            arg.update_info()

        self.check_method()

    def check_method(self):
        typ = self.typ
        while typ != None:
            if self.method in types[typ.name].methods:
                if type(self.val) == Field:
                    var_list[current_class][self.val.name].typs.add(typ) 
                elif type(self.val) == Var:
                    var_list[current_class][current_function][self.val.name].typs.add(typ)
                self.typ = typ
                return
            else:
                typ = types[typ.name].parent
                if typ != None:
                    typ = types[typ.name]
    
        sys.stderr.write(f"ERROR: {self.typ} does not have a {self.method} method\n")
        sys.exit(1)

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
        global current_function; current_function = self.name

        params = []
        for param in self.params:
            params.append(param) 

        if len(params) > 0:
            params = ".args " + ",".join(params) + "\n"
        else:
            params = ""

        local = []
        for var in var_list[current_class][current_function]:
            if not var_list[current_class][current_function][var].param:
                local.append(var)

        if len(local) > 0:
            local = ".local " + ",".join(local) + "\n"
        else:
            local = ""

        program = ""
        for line in self.program:
            program += line.get_assembly()

        if self.ret is None:
            ret = "\tconst nothing\n"
        else:
            if type(self.ret) == Field:
                ret = f"\tload {self.ret.val}\n\tload_field {self.ret.val}:{self.ret.name}\n"
            else:
                ret = self.ret.get_assembly()

        current_function = "Constr"

        text = f".method {self.name}\n{params}{local}\tenter\n{program}{ret}\treturn {len(self.params)}\n"
        return text

    def update_info(self):
        global current_function; current_function = self.name

        var_list[current_class][current_function] = {}

        params = {}
        for param in self.params:
            params[param] = self.params[param]
            v = Var(param, types[self.params[param]])
            v.param = True
            var_list[current_class][current_function][param] = v

        for parts in self.program:
            parts.update_info()

        if self.ret is not None:
            if type(self.ret) == str:
                index = self.ret.find(".")
                if index == -1:
                    self.ret = var_list[current_class][current_function][self.ret]
                else:
                    name = self.ret.split(".")
                    if name[0] == "$" or name[0] == "this":
                        self.ret = var_list[current_class][name[1]]
                    else:
                        self.ret = var_list[name[0]][name[1]]

            self.ret.update_info()

        types[current_class].methods[self.name] = Method(self.name, self.typ, params)

        current_function = "Constr"

class Class(ASTNode):
    def __init__(self, name, params, parent, code, funcs):
        super().__init__()
        self.name = name
        self.params = params
        self.parent = parent 
        self.code = code
        self.funcs = funcs

    def __str__(self):
        return f"Class: {self.name}"

    def get_assembly(self):
        global current_class; current_class = self.name

        code = ".method $constructor\n"

        local = ""
        local_li = []
        for var in var_list[current_class][current_function]:
            if not var_list[current_class][current_function][var].param:
                local.append(var_list[current_class][current_function][var])

        if len(local_li) > 0:
            local = ".local " + ",".join(local) + "\n"

        if len(self.params) > 0:
            code += ".args "
            li = []
            for param in self.params:
                li.append(param)
            code += ",".join(li) + "\n"

        code += f"{local}\tenter\n"

        for line in self.code:
            code += line.get_assembly()

        funcs = []
        for func in self.funcs:
            funcs.append(self.funcs[func].get_assembly())

        funcs = "\n".join(funcs)

        fields = ""
        for key in var_list[current_class]:
            if key != "Constr" and key not in types[current_class].methods:
                fields += f".field {key}\n"

        current_class = "Global"

        with open(f"{self.name}.asm", "w") as fil:
            fil.write(f".class {self.name}:{self.parent}\n{fields}{code}\tload $\n\treturn {len(self.params)}\n\n{funcs}")
        return ""

    def update_info(self):
        global current_class; current_class = self.name

        var_list[current_class] = {"Constr": {}}
        types[self.name] = Type(self.name, types[self.parent], {}, {})
        file_list.append(self.name)

        for param in self.params:
            v = Var(param, types[self.params[param]])
            v.valid = True
            v.param = True
            var_list[current_class][current_function][param] = v

        for item in self.code:
            item.update_info()

        for func in self.funcs:
            self.funcs[func].update_info()

        current_class = "Global"

class Instance(ASTNode):
    def __init__(self, name, args):
        super().__init__()
        self.name = name
        self.args = args

    def get_assembly(self):
        ret = ""
        for arg in self.args:
            ret += arg.get_assembly()

        return f"{ret}\tnew {self.name}\n\tcall {self.name}:$constructor\n"

    def update_info(self):
        for arg in self.args:
            arg.update_info()

    def get_typ(self):
        return types[self.name]

# Constants

class Const(ASTNode):
    def __init__(self, val):
        super().__init__()
        self.val = val

    def get_assembly(self):
        return f"\tconst {self.val}\n"

    def get_typ(self):
        return self.typ

class Number(Const):
    def __init__(self, val):
        super().__init__(val)

    def update_info(self):
        self.typ = types["Int"]

class String(Const):
    def __init__(self, val):
        super().__init__(val)

    def update_info(self):
        self.typ = types["String"]

class Bool(Const):
    def __init__(self, val):
        super().__init__(val)

    def update_info(self):
        self.typ = types["String"]

# Variables

class Var(ASTNode):
    def __init__(self, name, typ):
        super().__init__()
        self.name = name
        self.typs = set()
        self.typs.add(typ)
        self.valid = False
        self.param = False

    def get_typ(self):
        typs = list(self.typs)
        while len(typs) > 1:
            typ0 = typs.pop()
            typ1 = typs.pop()
            typs.append(typ0.get_common_ancestor(typ1))
        return typs[0]

    def get_assembly(self):
        assert self.valid, f"Variable {self.name} has not been initialized before use"
        return f"\tload {self.name}\n"

    def update_info(self):
        self.valid = True

class Field(Var):
    def __init__(self, val, name, typ):
        super().__init__(name, typ)
        self.val = val
        if self.val == "this":
            self.val = "$"

    def get_assembly(self):
        assert self.valid, f"Field {self.name} has not been initialized before use"
        return f"\tload {self.val}\n\tload_field $:{self.name}\n"

    def update_info(self):
        self.valid = True

class Assignment(ASTNode):
    def __init__(self, name, val):
        super().__init__()
        self.name = name
        self.val = val
        self.typ = "Unknown"

    def get_assembly(self):
        self.name.valid = True
        val = self.val.get_assembly();
        store = "store"

        if type(self.name) == Field:
            name = f"$:{self.name.name}\n"
            store = f"load {self.name.val}\n\tstore_field"
        else:
            name = self.name.name + "\n"
        return f"{val}\t{store} {name}"

    def update_info(self):
        index = self.name.find(".")
        if index == -1:
            if type(self.val) == str:
                self.val = var_list[current_class][current_function][self.name]

            self.val.update_info()

            var_list[current_class][current_function][self.name] = Var(self.name, self.val.get_typ())
            self.name = var_list[current_class][current_function][self.name]
            self.name.update_info()
        else:
            name = self.name.split(".")
            if type(self.val) == str:
                self.val = var_list[current_class][current_function][name[1]]

            self.val.update_info()

            var_list[current_class][name[1]] = Field(name[0], name[1], self.val.get_typ())
            if name[0] == "$" or name[0] == "this":
                self.name = var_list[current_class][name[1]]
            else:
                self.name = var_list[name[0]][name[1]]
            self.name.update_info()

        self.typ = self.name.get_typ()

@v_args(inline=True)    # Affects the signatures of the methods
class BuildTree(Transformer):
    def program(self, left, right):
        return Program(left, right)
    
    def statement(self, node):
        return node

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

    def methodcall(self, val, method, args=[]):
        return Methodcall(val, str(method), args)

    def field(self, val, field):
        return f"{val}.{field}"
    
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

    def ret(self, val):
        return val

    def class_create(self, name, args):
        ins = Instance(str(name), args)
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

    def func(self, name, params, typ, program, ret=None):
        func = Function(name, params, typ, program, ret)
        return func

    def plus(self, a, b):
        return Methodcall(a, "plus", [b])

    def sub(self, a, b):
        return Methodcall(a, "sub", [b])

    def mult(self, a, b):
        return Methodcall(a, "mult", [b])

    def div(self, a, b):
        return Methodcall(a, "div", [b])

    def eq(self, a, b):
        return Methodcall(a, "equals", [b])

    def lt(self, a, b):
        return Methodcall(a, "less", [b])

def main():
    if len(sys.argv) != 2:
        print("Usage: python3 parser.py [name]")
        return

    with open(sys.argv[1]) as f:
        s = f.read()

    filename = sys.argv[1].split("/")[-1].split(".")[-2]

    file_list.append(filename)

    output = f".class {filename}:Obj\n.method $constructor\n"
    if len(var_list["Global"]["Constr"]) > 0:
        output += ".local "
        li = []
        for var in var_list["Global"]["Constr"]:
            li.append(var)
        output += ",".join(li)
    output += "\tenter\n"

    tree = Lark(quack_grammar, parser="lalr", transformer=BuildTree()).parse(s)
    tree.update_info()
    output += tree.get_assembly()
    output += "\tconst nothing\n\treturn 0"

    with open(filename + ".asm", "w") as f:
        f.write(output)

    print("\n".join(reversed(file_list)))

if __name__ == '__main__':
    main()
