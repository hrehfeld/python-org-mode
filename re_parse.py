import re

enclosed = lambda x, s, e=None: s + x + (s if e is None else e)

esc_ = re.escape
g_ = lambda s: r'(?:%s)' % s
or_ = lambda *args: g_('|'.join(args))
in_ = lambda *args: r'[%s]' % (''.join(args))
nin_ = lambda *args: r'[^%s]' % (''.join(args))

#only supported in py 3.6
#i_ = lambda s: r'(?i:%s)' % s
def i_(s):
    def f(s):
        assert(s not in r'*-\\|()[]{}')
        
        a, b = s.lower(), s.upper()
        return in_(a + b) if a != b else a
    return ''.join([f(c) for c in s])

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
not_ = lambda s: r'(?!%s)' % s

ref_ = lambda name: r'(?P=%s)' % name
ref_yes_no_ = lambda name, yes, no: r'(?(%s)%s|%s)' % (name, yes, no)
def careful(s):
    assert(s[-1] in '+*')
    return g_(s) + '?'

lax = lambda lax, strict=None: lax if strict is None else or_(strict, lax) 
lax_only = lambda lax, strict=None: lax


eol = '\n'
ws_chars = ' \t'
ws1 = in_(ws_chars)
ws = ws1 + '+'
ows = ws1 + '*'
ows1 = ws1 + '?'
nws1 = nin_(ws_chars)
nws = nws1 + '+'

chars = r'\w+'
any = r'.+'
num = in_('0-9') + '+'
