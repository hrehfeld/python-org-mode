enclosed = lambda x, s, e=None: s + x + (s if e is None else e)

i_ = lambda s: r'(?i:%s)' % s
g_ = lambda s: r'(?:%s)' % s
or_ = lambda *args: g_('|'.join(args))
in_ = lambda *args: r'[%s]' % (''.join(args))
def re_count(s):
    if isinstance(s, str):
        assert(s in '*+?')
        return s
    elif isinstance(s, int):
        return '{%s}' % s
    return '{%s,%s}' % s
n_ = lambda s,n='+': g_(s) + re_count(n)
o = lambda s: g_(s) + '?'
g = lambda n, s: r'(?P<%s>%s)' % (n, s)
ref_ = lambda name: r'(?P=%s)' % name
ref_yes_no_ = lambda name, yes, no: r'(?(%s)%s|%s)' % (name, yes, no)
def careful(s):
    assert(s[-1] in '+*')
    return g_(s) + '?'

lax = lambda lax, strict=None: lax if strict is None else or_(strict, lax) 
lax_only = lambda lax, strict=None: lax


eol = '\n'
ws1 = ' '

drawer_key = lambda s: enclosed(s, ':')

def prop(name, value):
    return drawer_key(name) + ws1 + value

def drawer(name, values):
    r = [drawer_key(name)] + values + [drawer_key('END')]
    return eol.join(r)
