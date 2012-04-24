def f1(a):
    return int(a)

def f2(a):
    return (lambda i: len(str(i)))(a)

corpus = [f1, f2]
