from argparse import ArgumentParser
from code import interact
import imp
import opcode
import os
import random
import re
import types

import prettify

OPMAP = opcode.opmap
OP_HASBUILD = [OPMAP[n] for n in ("BUILD_TUPLE", "BUILD_LIST", "BUILD_MAP",
                                  "BUILD_SET")]
OP_HASCALL = [OPMAP[n] for n in ("CALL_FUNCTION", "CALL_FUNCTION_VAR",
                                 "CALL_FUNCTION_KW", "CALL_FUNCTION_VAR_KW")]
OP_HASMAKE = [OPMAP[n] for n in ("MAKE_FUNCTION", "MAKE_CLOSURE")]
OP_LITERALARG = opcode.hasjabs + opcode.hasjrel + OP_HASBUILD + OP_HASMAKE

MARKOV_START = -1
MARKOV_END = -2

def make_chain(funcs):
    chain = {}
    for func in funcs:
        _parse_func(func, chain)
    return chain

def make_function(chain, name, argcount=1):
    codes, constants, names, varnames = _make_codes(chain)
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
                target = "{0}({1!r})".format(target, tcode[1])
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
        print opcode.opname[code].rjust(20), str(i).rjust(3),
        i += 1
        if code >= opcode.HAVE_ARGUMENT:
            arg = _get_argument(codeobj, codestring, i, code)
            i += 2
            if code in opcode.hascompare:
                print " ({0})".format(arg)
            elif code in opcode.hasjabs:
                print " (to {0})".format(arg)
            elif code in opcode.hasjrel:
                print " (+{0})".format(arg)
            elif code in OP_HASBUILD:
                print " ({0} items)".format(arg)
            elif code in OP_HASCALL:
                print " ({0} args, {1} kwargs)".format(*arg)
            elif code in OP_HASMAKE:
                print " ({0} defaults)".format(arg)
            else:
                print " ({0!r})".format(arg)
        else:
            print

def run():
    parser = ArgumentParser(prog="func-smash",
                            description="Smash functions together!")
    parser.add_argument("path", metavar="path", help="path to the corpus file")
    parser.add_argument("-n", "--no-run", action="store_true",
                        help="don't run the function after smashing it")
    parser.add_argument("-i", "--interpret", action="store_true",
                        help="open a interpreter session after smashing")
    parser.add_argument("-p", "--prettify", action="store_true",
                        help="prettify the function after smashing it")
    args = parser.parse_args()

    path, name = os.path.split(args.path)
    name = re.sub("\.pyc?$", "", name)
    file_obj, path, desc = imp.find_module(name, [path])
    try:
        module = imp.load_module(name, file_obj, path, desc)
    finally:
        file_obj.close()

    corpus = module.corpus
    chain = make_chain(corpus)
    func = make_function(chain, "func")
    print "Using {0}-function corpus.".format(len(corpus))
    print "Smashed function disassembly:"
    print_function(func)
    
    if args.prettify:
        print "\nFunction as python code:"
        prettify.prettify_function(func, indent=4)

    if not args.no_run:
        arg = 12
        print
        print "func({0}) =".format(arg), func(arg)

    if args.interpret:
        variables = dict(globals().items() + locals().items())
        interact(banner="", local=variables)

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
    elif code in opcode.hasname:
        return codeobj.co_names[arg]
    elif code in opcode.haslocal:
        return codeobj.co_varnames[arg]
    elif code in opcode.hascompare:
        return opcode.cmp_op[arg]
    elif code in OP_HASCALL:
        return (ord(codestring[i]), ord(codestring[i + 1]))
    elif code in OP_LITERALARG:
        return arg
    raise NotImplementedError(code, opcode.opname[code])

def _chain_append(chain, first, second):
    try:
        chain[first].append(second)
    except KeyError:
        chain[first] = [second]

def _make_codes(chain):
    codes = []
    instruction = random.choice(chain[MARKOV_START])
    constants, names, varnames = [], [], []
    while 1:
        code, arg = instruction
        if code == MARKOV_END:
            break
        codes.append(code)
        if code >= opcode.HAVE_ARGUMENT:
            if code in opcode.hasconst:
                if arg not in constants:
                    constants.append(arg)
                _coerce_arg_into_codes(codes, constants.index(arg))
            elif code in opcode.hasname:
                if arg not in names:
                    names.append(arg)
                _coerce_arg_into_codes(codes, names.index(arg))
            elif code in opcode.haslocal:
                if arg not in varnames:
                    varnames.append(arg)
                _coerce_arg_into_codes(codes, varnames.index(arg))
            elif code in opcode.hascompare:
                _coerce_arg_into_codes(codes, opcode.cmp_op.index(arg))
            elif code in OP_HASCALL:
                codes.append(arg[0])
                codes.append(arg[1])
            elif code in OP_LITERALARG:
                _coerce_arg_into_codes(codes, arg)
            else:
                raise NotImplementedError(code, opcode.opname[code])
        instruction = random.choice(chain[code])
    return codes, tuple(constants), tuple(names), tuple(varnames)

def _opcode_to_opname(code):
    if code == MARKOV_START:
        return "START"
    elif code == MARKOV_END:
        return "END"
    return opcode.opname[code]

def _coerce_arg_into_codes(codes, arg):
    codes.append(arg % 256)
    codes.append(arg // 256)

if __name__ == "__main__":
    run()
