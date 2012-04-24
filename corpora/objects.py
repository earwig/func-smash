def f1(a):
    return [a] * 4

def f2(a):
    return (a,) + (1, 2)

def f3(a):
    return {a: 3}

def f4(a):
    return {a, 5}

corpus = [f1, f2, f3, f4]
