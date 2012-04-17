import opcode
import random
import types

############## CODE ###########################################################

MARKOV_START = -1
MARKOV_END = -2

def make_chain(funcs):
    chain = {}
    for func in funcs:
        _parse_func(func, chain)
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

def print_chain(chain):
    print "{"
    for key in sorted(chain.keys()):
        op = _int_to_opname(key)
        targets = {}
        for op2 in chain[key]:
            target = _int_to_opname(op2[0])
            if op2[0] >= opcode.HAVE_ARGUMENT:
                target = "{0}({1})".format(target, op2[1])
            try:
                targets[target] += 1
            except KeyError:
                targets[target] = 1
        targs = []
        for optarget, count in targets.iteritems():
            if count == 1:
                targs.append(optarget)
            else:
                targs.append("{0}x {1}".format(count, optarget))
        targs.sort()
        print op.rjust(20), "=> [{0}]".format(", ".join(targs))
    print "}"

def print_function(func):
    co = func.__code__
    code = co.co_code
    n = len(code)
    i = 0
    while i < n:
        op = ord(code[i])
        i += 1
        print opcode.opname[op].rjust(20),
        if op >= opcode.HAVE_ARGUMENT:
            arg = _get_argument(co, code, i, op)
            i += 2
            print " ({0})".format(arg)
        else:
            print

def _parse_func(func, chain):
    co = func.__code__
    code = co.co_code
    n = len(code)
    i = 0
    lastop = MARKOV_START
    while i < n:
        op = ord(code[i])
        i += 1
        if op >= opcode.HAVE_ARGUMENT:
            arg = _get_argument(co, code, i, op)
            i += 2
        else:
            arg = None
        _chain_append(chain, lastop, (op, arg))
        lastop = op
    _chain_append(chain, op, (MARKOV_END, None))

def _get_argument(co, code, i, op):
    oparg = ord(code[i]) + ord(code[i + 1]) * 256
    if op in opcode.hasconst:
        return co.co_consts[oparg]
    elif op in opcode.haslocal:
        return co.co_varnames[oparg]
    elif op in opcode.hascompare:
        return opcode.cmp_op[oparg]
    raise NotImplementedError(op, opcode.opname[op])

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
        op, arg = code
        if op == MARKOV_END:
            break
        codes.append(op)
        if op >= opcode.HAVE_ARGUMENT:
            if op in opcode.hasconst:
                if arg not in constants:
                    constants.append(arg)
                args = constants
            elif op in opcode.haslocal:
                if arg not in varnames:
                    varnames.append(arg)
                args = varnames
            elif op in opcode.hascompare:
                args = opcode.cmp_op
            else:
                raise NotImplementedError(op, opcode.opname[op])
            codes.append(args.index(arg) % 256)
            codes.append(args.index(arg) // 256)
        code = random.choice(chain[op])
    return codes, tuple(constants), tuple(varnames)

def _int_to_opname(op):
    if op == MARKOV_START:
        return "START"
    elif op == MARKOV_END:
        return "END"
    return opcode.opname[op]

############## FUNCTION CORPUS ################################################

def f1(a):
    b = a + 9.0
    return b

def f2(a):
    b = a - 7.0
    return b

def f3(a):
    b = a * 5.0
    return b

def f4(a):
    b = a / 3.0
    return b

def f5(a):
    b = a ** 2.0
    return b

def f6(a):
    b = a % 10.0
    return b

corpus = [f1, f2, f3, f4, f5, f6]

############## DEMO ###########################################################

if __name__ == "__main__":
    chain = make_chain(corpus)
    func = make_function(chain, "func")
    print "Using {0}-function corpus.".format(len(corpus))
    print "Smashed function disassembly:"
    print_function(func)
    print
    n = 12.0
    print "func(%s) =" % n, func(n)
