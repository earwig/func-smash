import opcode
import sys

import func_smash

OP_LOAD = {"LOAD_CONST": True, "LOAD_FAST": False, "LOAD_GLOBAL": False}
OP_BINARY = {"BINARY_POWER": "**", "BINARY_MULTIPLY": "*",
             "BINARY_DIVIDE": "/", "BINARY_MODULO": "%", "BINARY_ADD": "+",
             "BINARY_SUBTRACT": "-", "BINARY_FLOOR_DIVIDE": "//",
             "BINARY_TRUE_DIVIDE": "/", "BINARY_LSHIFT": "<<",
             "BINARY_RSHIFT": ">>", "BINARY_AND": "&", "BINARY_XOR": "^",
             "BINARY_OR": "|"}
OP_INPLACE = {"INPLACE_FLOOR_DIVIDE": "//", "INPLACE_TRUE_DIVIDE": "/",
              "INPLACE_ADD": "+", "INPLACE_SUBTRACT": "-",
              "INPLACE_MULTIPLY": "*", "INPLACE_DIVIDE": "/",
              "INPLACE_MODULO": "%", "INPLACE_POWER": "**",
              "INPLACE_LSHIFT": "<<", "INPLACE_RSHIFT": ">>",
              "INPLACE_AND": "&", "INPLACE_XOR": "^", "INPLACE_OR": "|"}
OP_SUBSCR = ("BINARY_SUBSCR", "INPLACE_SUBSCR")
OP_BUILD = {"BUILD_TUPLE": ("(", ")"), "BUILD_LIST": ("[", "]"),
               "BUILD_SET": ("{", "}")}

TAB = 4

def prettify_function(func, indent=0):
    args = _get_func_args(func)
    _print(indent, "def {0}({1}):".format(func.func_name, args))
    prettify_code(func.__code__, indent=indent+TAB)

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

    block = _parse_codestring(codes)
    block.display(indent)

def _get_func_args(func):
    codeobj = func.__code__
    count = codeobj.co_argcount
    if count == 0:
        return ""
    return ", ".join([arg for arg in codeobj.co_varnames[:count]])

def _parse_codestring(codes):
    stack = Stack()
    print_buffer = []
    main_block = block = Block()
    i2block = {}
    drops = []
    elses = []
    i = 0
    for instruction in codes:
        code, arg = instruction
        opname = opcode.opname[code]
        while i in elses:
            elses.remove(i)
            block.toggle()
        while i in drops:
            drops.remove(i)
            block = block.parent()
        i2block[i] = block
        if code >= opcode.HAVE_ARGUMENT:
            i += 3
        else:
            i += 1
        if opname in OP_LOAD:
            stack.push(arg, is_literal=OP_LOAD[opname])
        elif opname in OP_BINARY:
            tos, tos1 = stack.pop(), stack.pop()
            stack.push(" ".join((tos1, OP_BINARY[opname], tos)))
        elif opname in OP_INPLACE:  # Works, but doesn't use inplace op magic
            tos, tos1 = stack.pop(), stack.pop()
            stack.push(" ".join((tos1, OP_INPLACE[opname], tos)))
        elif opname in OP_SUBSCR:
            tos, tos1 = stack.pop(), stack.pop()
            stack.push("{0}[{1}]".format(tos1, tos))
        elif opname in OP_BUILD:
            args = []
            for i in xrange(arg):
                args.append(stack.pop())
            args.reverse()
            start, end = OP_BUILD[opname]
            stack.push(start + ", ".join(args) + end)
        elif opname == "BUILD_MAP":
            stack.push("{}")
        elif opname == "STORE_FAST":
            block.put(arg, "=", stack.pop())
        elif opname == "STORE_MAP":
            key, value = stack.pop(), stack.pop()
            pair = ": ".join((key, value))
            oldmap = stack.pop()
            if oldmap == "{}":
                newmap = "{" + pair + "}"
            else:
                newmap = oldmap[:-1] + ", " + pair + "}"
            stack.push(newmap)
        elif opname == "LOAD_ATTR":
            tos = stack.pop()
            new_tos = tos + "." + arg
            stack.push(new_tos)
        elif opname == "POP_TOP":
            block.put(stack.pop())
        elif opname == "CALL_FUNCTION":
            numargs, numkwargs = arg
            args = []
            for i in xrange(numkwargs):
                value = stack.pop()
                key = stack.pop(never_literal=True)
                args.append("=".join((key, value)))
            for i in xrange(numargs):
                args.append(stack.pop())
            args.reverse()
            funcname = stack.pop()
            stack.push("{0}({1})".format(funcname, ", ".join(args)))
        elif opname == "PRINT_ITEM":
            print_buffer.append(stack.pop())
        elif opname == "PRINT_NEWLINE":
            block.put("print", ", ".join(print_buffer))
            print_buffer = []
        elif opname == "RETURN_VALUE":
            block.put("return", stack.pop())
        elif opname == "COMPARE_OP":
            tos, tos1 = stack.pop(), stack.pop()
            compare = " ".join((tos1, arg, tos))
            stack.push(compare)
        elif opname == "POP_JUMP_IF_FALSE":
            block = block.child()
            block.split(stack.pop())
            elses.append(arg)
        elif opname == "POP_JUMP_IF_TRUE":
            block = block.child()
            block.split(stack.pop())
            elses.append(arg)
        elif opname == "JUMP_ABSOLUTE":
            if arg < i:
                block = block.parent()
            else:
                drops.append(arg)
        elif opname == "JUMP_FORWARD":
            drops.append(arg + i)
        elif opname == "SETUP_LOOP":
            block = block.child(loop=True)
        elif opname == "POP_BLOCK":
            block = block.parent()
        else:
            raise NotImplementedError(opname, arg, stack)

    return main_block

def _print(indentation, *args, **kwargs):
    argstring = " ".join([str(arg) for arg in args if str(arg)])
    if kwargs.get("debug"):
        # Ignore debug messages without -d flag
        if len(sys.argv) > 1 and sys.argv[1] == "-d":
            print " " * 50 + "#", argstring
        return
    print " " * indentation + argstring


class Stack(object):
    def __init__(self):
        self._items = []

    def __iter__(self):
        while self._items:
            yield self.pop()

    def __repr__(self):
        s = reversed([repr(itm) if lit else itm for itm, lit in self._items])
        return "Stack[" + ", ".join(s) + "]"

    def push(self, item, is_literal=False):
        self._items.append((item, is_literal))

    def pop(self, never_literal=False):
        item, is_literal = self._items.pop()
        return repr(item) if is_literal and not never_literal else item


class Block(object):
    def __init__(self, parent=None, loop=False):
        self._parent = parent
        self._loop = loop
        self._true_block = self._focus = []
        self._false_block = []
        self._split = None

    def __iter__(self):
        for item in self._render_lines():
            yield item[1]

    def __repr__(self):
        return str([item[1] for item in self._render_lines()])

    def _has_lines(self):
        return self._split or self._true_block or self._false_block

    def _render_subblock(self, block, lines, indent):
        for item in block:
            if isinstance(item, Block):
                lines += item._render_lines(indent)
            else:
                lines.append((indent, item))

    def _render_lines(self, indent=0):
        lines = []
        if self._split:
            lines.append((indent, (self._split,)))
            indent += TAB
        self._render_subblock(self._true_block, lines, indent)
        if self._false_block:
            lines.append((indent - TAB, ("else:",)))
            self._render_subblock(self._false_block, lines, indent)
        return lines

    def child(self, loop=False):
        if self._loop and not loop and not self._has_lines():
            loop = True 
        child = Block(parent=self, loop=loop)
        self._focus.append(child)
        return child

    def parent(self):
        if self._parent:
            return self._parent
        raise RuntimeError("Popping an orphaned block")

    def put(self, *code):
        self._focus.append(code)

    def split(self, test):
        if self._loop:
            self._split = "while " + test + ":"
        else:
            self._split = "if " + test + ":"

    def toggle(self):
        if self._focus is self._true_block:
            self._focus = self._false_block
        else:
            self._focus = self._true_block

    def display(self, indent=0):
        for indent, code in self._render_lines(indent):
            _print(indent, *code)


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

    def f3(x, y):
        if cmp1:
            while cmp1:
                if cmp2:
                    while cmp3:
                        line1
        else:
            while cmp4:
                line2
                line3
                line4
                if cmp5:
                    line5
        return line6

    prettify_function(f1)
    print
    prettify_function(f2)
    print
    prettify_function(f3)
