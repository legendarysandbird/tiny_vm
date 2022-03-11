# Possible types
class Type:
    def __init__(self, name, parent, methods, props):
        self.name = name
        self.parent = parent
        self.methods = methods
        self.props = props

    def __str__(self):
        return f"{self.name.upper()}"

    def __repr__(self):
        return f"Type({self.name}, {self.parent}, {self.methods}, {self.props})"

    # Find common ancestor when you have more than one type
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

# Holds information about methods on classes 
class Method():
    def __init__(self, name, ret, params):
        self.name = name
        self.ret = ret
        self.params = params

# Common Methods
STR = Method("string", "String", {})
PRNT = Method("print", "Nothing", {})
EQLS = Method("equals", "Boolean", {})
LESS = Method("less", "Boolean", {})
GREATER = Method("greater", "Boolean", {})
LE = Method("LE", "Boolean", {})
GE = Method("GE", "Boolean", {})
CAT = Method("plus", "String", {})
PLUS = Method("plus", "Int", {})
SUB = Method("sub", "Int", {})
MULT = Method("mult", "Int", {})
DIV = Method("div", "Int", {})

# Builtin types
Obj = Type("Obj", None, {"string": STR, "print": PRNT, "equals": EQLS}, {})
String = Type("String", Obj, {"string": STR, "print": PRNT, "equals": EQLS, "less": LESS, "greater": GREATER, "LE": LE, "GE": GE, "plus": CAT}, {})
Int = Type("Int", Obj, {"plus": PLUS, "sub": SUB, "mult": MULT, "div": DIV, "less": LESS, "greater": GREATER, "GE": GE, "LE": LE, "equals": EQLS, "print": PRNT, "string": STR}, {})
Boolean = Type("Boolean", Obj, {"string": STR, "print": PRNT, "equals": EQLS}, {})
Nothing = Type("Nothing", None, {}, {})

types = {
        "Obj": Obj,
        "String": String,
        "Int": Int,
        "Boolean": Boolean,
        "Nothing": Nothing
        }
