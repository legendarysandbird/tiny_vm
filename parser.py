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
and_count = 0
or_count = 0
not_count = 0

# Namespace trackers
current_class = "Global"
current_function = "Constr"

# Global information
node_list = []
var_list = {"Global": {"Constr": {}}}
file_list = []

# Abstract Base Class
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

class And(ASTNode):
    def __init__(self, left, right):
        self.left = left
        self.right = right

    def get_assembly(self):
        global and_count
        left = self.left.get_assembly()
        right = self.right.get_assembly()
        msg = f"{left}\tjump_ifnot and_mid{and_count}\n{right}\tjump and_end{and_count}\nand_mid{and_count}:\n\tconst false\nand_end{and_count}:\n"
        and_count += 1
        return msg

    def update_info(self):
        self.left.update_info()
        self.right.update_info()

class Or(ASTNode):
    def __init__(self, left, right):
        self.left = left
        self.right = right

    def get_assembly(self):
        global or_count
        left = self.left.get_assembly()
        right = self.right.get_assembly()
        msg = f"{left}\tjump_if or_mid{or_count}\n{right}\tjump or_end{or_count}\nor_mid{or_count}:\n\tconst true\nor_end{or_count}:\n"
        or_count += 1
        return msg

    def update_info(self):
        self.left.update_info()
        self.right.update_info()

class Not(ASTNode):
    def __init__(self, cond):
        self.cond = cond

    def get_assembly(self):
        global not_count
        cond = self.cond.get_assembly()
        msg = f"{cond}\tjump_if not_mid{not_count}\n\tconst true\n\tjump not_end{not_count}\n\tnot_mid{not_count}:\t\nconst false\n\tnot_end{not_count}:\n"
        not_count += 1
        return msg

    def update_info(self):
        self.cond.update_info()

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
        
    def get_assembly(self):
        val = self.val.get_assembly()

        arg = ""
        for argu in self.args:
            arg += argu.get_assembly()

        roll = ""

        if self.method == "sub" or self.method == "div" or self.method == "less" or self.method == "plus":
            roll = "\troll 1\n"

        if self.val.get_typ().name in var_list:
            text = f"{arg}{val}{roll}\tcall {self.typ.name}:{self.method}\n"
        else:
            text = f"{val}{arg}{roll}\tcall {self.typ.name}:{self.method}\n"

        if self.method == "print":
            text += "\tpop\n"

        return text

    def update_info(self):
        self.val.update_info()
        self.typ = self.val.get_typ()
        for arg in self.args:
            arg.update_info()

        self.check_method()

    def check_method(self):
        typ = self.val.get_typ()
        while typ != None:
            if self.method in types[typ.name].methods:
                self.typ = types[typ.name]
                return
            else:
                typ = types[typ.name].parent
                if typ != None:
                    typ = types[typ.name]
    
        sys.stderr.write(f"ERROR: {self.typ} does not have a {self.method} method\n")
        sys.exit(1)

    def get_typ(self):
        return self.typ

# Containers
class Function(ASTNode):
    def __init__(self, name, params, typ, program, ret):
        super().__init__()
        self.name = str(name)
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
            v = VarType()
            v.add_typ(types[self.params[param]])
            v.param = True
            v.valid = True
            var_list[current_class][current_function][param] = v

        for parts in self.program:
            parts.update_info()

        if self.ret is not None:
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
            v = VarType()
            v.add_typ(types[self.params[param]])
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
        self.typ = types["Boolean"]

# Variables
class VarType():
    def __init__(self):
        self.typs = set()
        self.valid = False
        self.param = False

    def add_typ(self, typ):
        self.typs.add(typ)

    def get_typ(self):
        typs = list(self.typs)
        while len(typs) > 1:
            typ0 = typs.pop()
            typ1 = typs.pop()
            typs.append(typ0.get_common_ancestor(typ1))
        return typs[0]

class VarCreate(ASTNode):
    def __init__(self, name):
        super().__init__()
        self.name = name

    def get_assembly(self):
        self.typ.valid = True
        return f"\tstore {self.name}\n"

    def update_info(self, typ):
        if self.name not in var_list[current_class][current_function]:
            v = VarType()
            v.add_typ(typ)
            self.typ = v
            var_list[current_class][current_function][self.name] = v
        else:
            var_list[current_class][current_function][self.name].add_typ(typ)
            self.typ = var_list[current_class][current_function][self.name]

    def get_typ(self):
        return self.typ.get_typ()

class VarCall(ASTNode):
    def __init__(self, name):
        super().__init__()
        self.name = name

    def get_assembly(self):
        assert self.typ.valid, f"Variable {self.name} has not been initialized before use"
        return f"\tload {self.name}\n"

    def update_info(self):
        assert self.name in var_list[current_class][current_function], f"Variable {self.name} has not been initialized before use"
        self.typ = var_list[current_class][current_function][self.name]

    def get_typ(self):
        return self.typ.get_typ()

class FieldCreate(ASTNode):
    def __init__(self, val, name):
        super().__init__()
        self.name = name
        self.val = val
        if self.val == "this":
            self.val = "$"

    def get_assembly(self):
        self.typ.valid = True
        return f"\tload {self.val}\n\tstore_field {self.val}:{self.name}\n"

    def update_info(self, typ):
        if self.name not in var_list[current_class]:
            v = VarType()
            v.add_typ(typ)
            self.typ = v
            var_list[current_class][self.name] = v
        else:
            var_list[current_class][self.name].add_typ(typ)
            self.typ = var_list[current_class][self.name]

    def get_typ(self):
        return self.typ.get_typ()


class FieldCall(ASTNode):
    def __init__(self, val, name):
        super().__init__()
        self.name = name
        self.val = val
        if self.val == "this":
            self.val = "$"

    def get_assembly(self):
        assert self.typ.valid, f"Field {self.name} has not been initialized before use"
        return f"\tload {self.val}\n\tload_field {self.val}:{self.name}\n"

    def update_info(self):
        assert self.name in var_list[current_class], f"Field {self.val}.{self.name} has not been initialized before use"
        self.typ = var_list[current_class][self.name]

    def get_typ(self):
        return self.typ.get_typ()

class Assignment(ASTNode):
    def __init__(self, name, val):
        super().__init__()
        self.name = name
        self.val = val

    def get_assembly(self):
        val = self.val.get_assembly();
        name = self.name.get_assembly();
        return f"{val}{name}"

    def update_info(self):
        self.val.update_info()
        self.name.update_info(self.val.get_typ())
        self.typ = self.val.get_typ()
        

@v_args(inline=True)    # Affects the signatures of the methods
class BuildTree(Transformer):
    def program(self, left, right):
        return Program(left, right)
    
    def statement(self, node):
        return node

    def typ(self, name):
        return str(name)

    def typed(self, name, typ, val):
        name = str(name)
        index = name.find(".")
        if index == -1:
            name = VarCreate(name)
        else:
            new_name = name.split(".")
            name = FieldCreate(new_name[0], new_name[1])

        return Assignment(name, val)

    def untyped(self, name, val):
        name = str(name)
        index = name.find(".")
        if index == -1:
            name = VarCreate(name)
        else:
            new_name = name.split(".")
            name = FieldCreate(new_name[0], new_name[1])

        return Assignment(name, val)

    def var_call(self, name):
        name = str(name)
        index = name.find(".")
        if index == -1:
            name = VarCall(name)
        else:
            new_name = name.split(".")
            name = FieldCall(new_name[0], new_name[1])

        return name

    def field(self, val, name):
        return f"{val}.{name}"

    def rexp(self, math_node):
        return math_node

    def number(self, val):
        return Number(val)

    def string(self, text):
        return String(text)

    def methodcall(self, val, method, args=[]):
        if type(val) == Token:
            val = str(val)
            index = val.find(".")
            if index == -1:
                val = VarCall(val)
            else:
                name = val.split(".")
                val = FieldCall(name[0], name[1])

        return Methodcall(val, str(method), args)

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

    def neg(self, a):
        return Methodcall(Number(0), "sub", [a])

    def mult(self, a, b):
        return Methodcall(a, "mult", [b])

    def div(self, a, b):
        return Methodcall(a, "div", [b])

    def eq(self, a, b):
        return Methodcall(a, "equals", [b])

    def lt(self, a, b):
        return Methodcall(a, "less", [b])
    
    def gt(self, a, b):
        return Methodcall(a, "greater", [b])

    def le(self, a, b):
        return Methodcall(a, "LE", [b])

    def ge(self, a, b):
        return Methodcall(a, "GE", [b])

    def log_and(self, left, right):
        return And(left, right)

    def log_or(self, left, right):
        return Or(left, right)
    
    def log_not(self, cond):
        return Not(cond)

def main():
    if len(sys.argv) != 2:
        print("Usage: python3 parser.py [name]")
        return

    with open(sys.argv[1]) as f:
        s = f.read()

    filename = sys.argv[1].split("/")[-1].split(".")[-2]
    file_list.append(filename)

    tree = Lark(quack_grammar, parser="lalr", transformer=BuildTree()).parse(s) # Build tree
    tree.update_info() # Fills in missing type information

    # Main file assembly
    output = f".class {filename}:Obj\n.method $constructor\n"
    if len(var_list["Global"]["Constr"]) > 0:
        output += ".local "
        li = []
        for var in var_list["Global"]["Constr"]:
            li.append(var)
        output += ",".join(li)
    output += "\tenter\n"

    # Closing assembly for main file
    output += tree.get_assembly()
    output += "\tconst nothing\n\treturn 0"

    with open(filename + ".asm", "w") as f:
        f.write(output)

    # List of built .asm files for the quack script
    print("\n".join(reversed(file_list)))

if __name__ == '__main__':
    main()
