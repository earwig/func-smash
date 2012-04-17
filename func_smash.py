import dis
import opcode
import random
import types

############## CODE ###########################################################

MARKOV_START = -1
MARKOV_END = -2

def make_chain(funcs):
    chain = {}
    for func in funcs:
        co = func.__code__
        code = co.co_code
        n = len(code)
        i = 0
        lastop = MARKOV_START
        while i < n:
            op = ord(code[i])
            i += 1
            if op >= opcode.HAVE_ARGUMENT:
                oparg = ord(code[i]) + ord(code[i + 1]) * 256
                i += 2
                if op in opcode.hasconst:
                    arg = co.co_consts[oparg]
                elif op in opcode.haslocal:
                    arg = co.co_varnames[oparg]
                else:
                    raise NotImplementedError(op, opcode.opname[op])
            else:
                arg = None
            _chain_append(chain, lastop, (op, arg))
            lastop = op
        _chain_append(chain, op, MARKOV_END)
    return chain

def make_function(chain, name, argcount=1):
    codes, constants, varnames = _make_codes(chain)
    nlocals = len(varnames) + argcount
    stacksize = 1024  # High limit?
    flags = 0  # Denotes funcs with *args and/or **kwargs; nothing for now
    codestring = "".join([chr(code) for code in codes])
    names = ()
    filename = "<smash>"
    firstlineno = 1
    lnotab = ""

    code = types.CodeType(argcount, nlocals, stacksize, flags, codestring,
                          constants, names, varnames, filename, name,
                          firstlineno, lnotab)
    func = types.FunctionType(code, globals(), name)
    return func

def _chain_append(chain, first, second):
    try:
        chain[first].append(second)
    except KeyError:
        chain[first] = [second]

def _make_codes(chain):
    codes = []
    code = random.choice(chain[MARKOV_START])
    constants, varnames = [], []
    while 1:
        if code == MARKOV_END:
            break
        op, arg = code
        codes.append(op)
        if op >= opcode.HAVE_ARGUMENT:
            if op in opcode.hasconst:
                args = constants
            elif op in opcode.haslocal:
                args = varnames
            else:
                raise NotImplementedError(op, opcode.opname[op])
            if arg not in args:
                args.append(arg)
            codes.append(args.index(arg))
            codes.append(0)
        code = random.choice(chain[op])
    return codes, tuple(constants), tuple(varnames)

############## FUNCTION CORPUS ################################################

def f1(a):
    b = a + 7.0
    return b

def f2(a):
    b = a - 5.0
    return b

def f3(a):
    b = a * 3.0
    return b

def f4(a):
    b = a / 2.0
    return b

corpus = [f1, f2, f3, f4]

############## DEMO ###########################################################

if __name__ == "__main__":
    print "USING FUNCTION CORPUS:", [func.__name__ for func in corpus]
    chain = make_chain(corpus)
    print "OPCODE MARKOV CHAIN:", chain
    print

    func = make_function(chain, "func")
    print "SMASHED FUNCTION CODE:", [ord(c) for c in func.__code__.co_code]
    print "FUNCTION DISASSEMBLY:"
    dis.dis(func)
    print
    n = 12.0
    print "func(%s) =" % n, func(n)
