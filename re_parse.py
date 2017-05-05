import re

enclosed = lambda x, s, e=None: s + x + s if e is None else e

esc_ = re.escape
i_ = lambda s: r'(?i:%s)' % s
g_ = lambda s: r'(?:%s)' % s
or_ = lambda *args: g_('|'.join(args))
def re_count(s):
    if isinstance(s, str):
        assert(s in '*+?')
        return s
    elif isinstance(s, int):
        s = s, ''
    return '{%s,%s}' % s
n_ = lambda s,n='+': g_(s) + re_count(n)
o = lambda s: g_(s) + '?'
g = lambda n, s: r'(?P<%s>%s)' % (n, s)
def careful(s):
    assert(s[-1] in '+*')
    return g_(s) + '?'

lax = lambda lax, strict=None: lax if strict is None else or_(strict, lax) 


eol = '\n'
ws_c = '[ \t]'
ws = n_(ws_c, '+')
ows = n_(ws_c, '*')
ws1 = ws_c
ows1 = o(ws_c)

chars = r'\w+'
any = r'.+'

