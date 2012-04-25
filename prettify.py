import opcode
import sys

import func_smash

OP_HASLOAD = {"LOAD_CONST": True, "LOAD_FAST": False, "LOAD_GLOBAL": False}
OP_HASBINARY = {"BINARY_ADD": "+", "BINARY_SUBTRACT": "-",
                "BINARY_MULTIPLY": "*", "BINARY_DIVIDE": "/",
                "BINARY_POWER": "**", "BINARY_MODULO": "%"}
OP_HASBUILD = {"BUILD_TUPLE": ("(", ")"), "BUILD_LIST": ("[", "]"),
               "BUILD_SET": ("{", "}")}

def prettify_function(func, indent=0):
    args = _get_func_args(func)
    _print(indent, "def {0}({1}):".format(func.func_name, args))
    prettify_code(func.__code__, indent=indent+4)

def prettify_code(codeobj, indent=0):
    codes = []
    codestring = codeobj.co_code
    length = len(codestring)
    i = 0
    while i < length:
        code = ord(codestring[i])
        i += 1
        if code >= opcode.HAVE_ARGUMENT:
            arg = func_smash._get_argument(codeobj, codestring, i, code)
            i += 2
            codes.append((code, arg))
        else:
            codes.append((code, None))
    _print_codestring(codes, indent)

def _print_codestring(codes, indent):
    stack = []
    print_buffer = []
    for instruction in codes:
        code, arg = instruction
        opname = opcode.opname[code]
        _print(indent, opname, arg, "; stack ==", stack, debug=True)
        if opname in OP_HASLOAD:
            _push(stack, arg, literal=OP_HASLOAD[opname])
        elif opname in OP_HASBINARY:
            tos, tos1 = _pop(stack), _pop(stack)
            _push(stack, " ".join((tos1, OP_HASBINARY[opname], tos)))
        elif opname in OP_HASBUILD:
            args = []
            for i in xrange(arg):
                args.append(_pop(stack))
            args.reverse()
            start, end = OP_HASBUILD[opname]
            _push(stack, start + ", ".join(args) + end)
        elif opname == "BUILD_MAP":
            _push(stack, "{}")
        elif opname == "STORE_FAST":
            _print(indent, arg, "=", _pop(stack))
        elif opname == "STORE_MAP":
            pair = ": ".join((_pop(stack), _pop(stack)))
            oldmap = _pop(stack)
            if oldmap == "{}":
                newmap = "{" + pair + "}"
            else:
                newmap = oldmap[:-1] + ", " + pair + "}"
            _push(stack, newmap)
        elif opname == "POP_TOP":
            _print(indent, _pop(stack))
        elif opname == "CALL_FUNCTION":
            numargs, numkwargs = arg
            args = []
            for i in xrange(numkwargs):
                value = _pop(stack)
                key = _pop(stack, never_literal=True)
                args.append("=".join((key, value)))
            for i in xrange(numargs):
                args.append(_pop(stack))
            args.reverse()
            funcname = _pop(stack)
            _push(stack, "{0}({1})".format(funcname, ", ".join(args)))
        elif opname == "PRINT_ITEM":
            print_buffer.append(_pop(stack))
        elif opname == "PRINT_NEWLINE":
            _print(indent, "print", ", ".join(print_buffer))
            print_buffer = []
        elif opname == "RETURN_VALUE":
            _print(indent, "return", _pop(stack))
        else:
            raise NotImplementedError(opname, arg, stack)

def _get_func_args(func):
    codeobj = func.__code__
    count = codeobj.co_argcount
    if count == 0:
        return ""
    return ", ".join([arg for arg in codeobj.co_varnames[:count]])

def _push(stack, item, literal=False):
    stack.append((item, literal))

def _pop(stack, never_literal=False):
    item, literal = stack.pop()
    return repr(item) if literal and not never_literal else item

def _print(indentation, *args, **kwargs):
    argstring = " ".join([str(arg) for arg in args if str(arg)])
    if kwargs.get("debug"):
        # Ignore debug messages without -d flag
        if len(sys.argv) > 1 and sys.argv[1] == "-d":
            print " " * 50 + "#", argstring
        return
    print " " * indentation + argstring

if __name__ == "__main__":
    def f1(a):
        b = a + 10 / 7.0
        d = long_func(a, b+9, c=42, d="43")
        print b, d
        ex_tuple = ("Hello", "world!", abcdef)
        ex_list = [1, 2, 3] * 3 + [4, 5, 6]
        ex_set = {99, 98, 97, 96, 95}
        ex_dict = {d: e, f: False, "testing": g}
        return ex_dict

    def f2():
        pass

    prettify_function(f1)
    print
    prettify_function(f2)
