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

    func: "def" lexp "(" params ")" ":" typ "{" block "return" rexp ";" "}"

    block: statement* 

    loop: "while" "(" rexp ")" "{" program "}"

    condif: "if" "(" rexp ")" "{" program "}" [condelif] [condelse]

    condelif: "elif" "(" rexp ")" "{" program "}" [condelif]

    condelse: "else" "{" program "}"

    methodcall: lexp "." NAME "(" ")"
        | lexp "." NAME "(" atom ")"
        | atom "." NAME "(" ")"
        | atom "." NAME "(" atom ")"

    class_create: NAME "(" args ")"

    rexp: relation

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
