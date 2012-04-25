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
    block_dedent_at = []
    block_else_at = []
    i = 0
    for instruction in codes:
        code, arg = instruction
        opname = opcode.opname[code]
        if code >= opcode.HAVE_ARGUMENT:
            i += 3
        else:
            i += 1
        for x in block_dedent_at:
            if i >= x:
                indent -= 4
                block_dedent_at.remove(x)
        for x in block_else_at:
            if i >= x:
                _print(indent, "else:")
                indent += 4
                _print(indent, "pass")
                block_else_at.remove(x)
        _print(indent, i, opname, arg, debug=True)
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
            key, value = _pop(stack), _pop(stack)
            pair = ": ".join((key, value))
            oldmap = _pop(stack)
            if oldmap == "{}":
                newmap = "{" + pair + "}"
            else:
                newmap = oldmap[:-1] + ", " + pair + "}"
            _push(stack, newmap)
        elif opname == "LOAD_ATTR":
            tos = _pop(stack)
            new_tos = tos + "." + arg
            _push(stack, new_tos)
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
        elif opname == "COMPARE_OP":
            tos, tos1 = _pop(stack), _pop(stack)
            compare = " ".join((tos1, arg, tos))
            _push(stack, compare)
        elif opname == "POP_JUMP_IF_FALSE":
            test = _pop(stack)
            _print(indent, "if {0}:".format(test))
            block_dedent_at.append(arg)
            block_else_at.append(arg)
            indent += 4
        elif opname == "JUMP_ABSOLUTE":
            block_dedent_at.append(i)
        elif opname == "JUMP_FORWARD":
            block_dedent_at.append(i + arg)
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

    def f2(a, b, c):
        if cmp1:
            line1
            if cmp2:
                line2
            elif cmp3:
                line3
            elif cmp4:
                line4
            else:
                line5
            line6
        else:
            line7
        line8
        if cmp4:
            line9
        if cmp5:
            if cmp6:
                if cmp7:
                    if cmp8:
                        if cmp9:
                            line10
        return line11

    prettify_function(f1)
    print
    prettify_function(f2)
