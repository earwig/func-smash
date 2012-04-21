from code import interact
import imp
import opcode
import os
import random
import re
import sys
import types

MARKOV_START = -1
MARKOV_END = -2

def make_chain(funcs):
    chain = {}
    for func in funcs:
        _parse_func(func, chain)
    return chain

def make_function(chain, name, argcount=1):
    codes, constants, varnames = _make_codes(chain)
    names = ()
    codestring = "".join([chr(code) for code in codes])
    lnotab = ""

    code = types.CodeType(argcount, len(varnames), 1024, 0, codestring,
                          constants, names, varnames, "<smash>", name, 1,
                          lnotab)
    func = types.FunctionType(code, globals(), name)
    return func

def print_chain(chain):
    print "{"
    for code in sorted(chain.keys()):
        name = _opcode_to_opname(code)
        target_counts = {}
        for tcode in chain[code]:
            target = _opcode_to_opname(tcode[0])
            if tcode[0] >= opcode.HAVE_ARGUMENT:
                target = "{0}({1})".format(target, tcode[1])
            try:
                target_counts[target] += 1
            except KeyError:
                target_counts[target] = 1
        targets = []
        for target, count in target_counts.iteritems():
            if count == 1:
                targets.append(target)
            else:
                targets.append("{0}x {1}".format(count, target))
        targets.sort()
        print name.rjust(20), "=> [{0}]".format(", ".join(targets))
    print "}"

def print_function(func):
    codeobj = func.__code__
    codestring = codeobj.co_code
    length = len(codestring)
    i = 0
    while i < length:
        code = ord(codestring[i])
        i += 1
        print opcode.opname[code].rjust(20),
        if code >= opcode.HAVE_ARGUMENT:
            arg = _get_argument(codeobj, codestring, i, code)
            i += 2
            print " ({0})".format(arg)
        else:
            print

def run():
    try:
        path, name = os.path.split(sys.argv[1])
        name = re.sub("\.pyc?$", "", name)
    except IndexError:
        raise RuntimeError("Needs a filename as a command-line argument")
    file_obj, path, desc = imp.find_module(name, [path])
    try:
        module = imp.load_module(name, file_obj, path, desc)
    finally:
        file_obj.close()

    _demo(module.corpus)

def _parse_func(func, chain):
    codeobj = func.__code__
    codestring = codeobj.co_code
    length = len(codestring)
    i = 0
    prevcode = MARKOV_START
    while i < length:
        code = ord(codestring[i])
        i += 1
        if code >= opcode.HAVE_ARGUMENT:
            arg = _get_argument(codeobj, codestring, i, code)
            i += 2
        else:
            arg = None
        _chain_append(chain, prevcode, (code, arg))
        prevcode = code
    _chain_append(chain, code, (MARKOV_END, None))

def _get_argument(codeobj, codestring, i, code):
    arg = ord(codestring[i]) + ord(codestring[i + 1]) * 256
    if code in opcode.hasconst:
        return codeobj.co_consts[arg]
    elif code in opcode.haslocal:
        return codeobj.co_varnames[arg]
    elif code in opcode.hascompare:
        return opcode.cmp_op[arg]
    raise NotImplementedError(code, opcode.opname[code])

def _chain_append(chain, first, second):
    try:
        chain[first].append(second)
    except KeyError:
        chain[first] = [second]

def _make_codes(chain):
    codes = []
    instruction = random.choice(chain[MARKOV_START])
    constants, varnames = [], []
    while 1:
        code, arg = instruction
        if code == MARKOV_END:
            break
        codes.append(code)
        if code >= opcode.HAVE_ARGUMENT:
            if code in opcode.hasconst:
                if arg not in constants:
                    constants.append(arg)
                args = constants
            elif code in opcode.haslocal:
                if arg not in varnames:
                    varnames.append(arg)
                args = varnames
            elif code in opcode.hascompare:
                args = opcode.cmp_op
            else:
                raise NotImplementedError(code, opcode.opname[code])
            codes.append(args.index(arg) % 256)
            codes.append(args.index(arg) // 256)
        instruction = random.choice(chain[code])
    return codes, tuple(constants), tuple(varnames)

def _opcode_to_opname(code):
    if code == MARKOV_START:
        return "START"
    elif code == MARKOV_END:
        return "END"
    return opcode.opname[code]

def _demo(corpus, arg=12.0):
    chain = make_chain(corpus)
    func = make_function(chain, "func")
    print "Using {0}-function corpus.".format(len(corpus))
    print "Smashed function disassembly:"
    print_function(func)
    print
    print "func({0}) =".format(arg), func(arg)

    if len(sys.argv) > 2 and sys.argv[2] == "-i":
        variables = dict(globals().items() + locals().items())
        interact(banner="", local=variables)

if __name__ == "__main__":
    run()
