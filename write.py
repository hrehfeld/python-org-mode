from collections import OrderedDict as odict

from str_build import *
from datetime import datetime

from org_re import warning

def compose(*funs):
    def do(*args):
        for f in reversed(funs):
            args = (f(*args),)
        return args[0]
    return do

def adder(x):
    return lambda s: x + s

class Writer:
    def str(self, indent=''):
        warning('there should never be a str')
        return indent + self

    def para(self, indent=''):
        r = map(lambda e: indent + e, self.content)
        return eol.join(r)

    empty = para

    def comment(self, indent=''):
        return indent + '# ' + str(self.value)

    def block(self, indent=''):
        start = indent + '#+begin_' + self.name
        if self.value:
            start += ws1 + self.value
        start += eol
        end = indent + '#+end_' + self.name
        return start + self.content + end

    def list(self, indent=''):
        l = map(lambda e: dumps(e, indent), self.content)
        r = eol.join(l)
        return r
    

    def listitem(self, indent=''):

        start = self.start() + ws1

        #assert(str(self.content[0])[-1] != eol)
        f = lambda c: dumps(c, indent + ws1 * len(start))
        c = dumps(self.content[0])
        cs = list(map(f, self.content[1:]))
        cs = [c] + cs
        cs = eol.join(cs)
        
        return indent + start + cs

    orderedlistitem = listitem

    definitionlistitem = listitem


    def drawer(self, indent=''):
        values = list(map(lambda e: dumps(e, indent), self.content))
        return drawer(self.name, values, indent)
        

    def attr(self, indent=''):
        return indent + '#+' + self.name + ': ' + (self.value or '')

    def node(self, indent):
        r = []
        #root

        if self.level > 0:
            s = ''
            s = '*' * self.level + ws1
            if self.keyword:
                s += self.keyword + ws1
            if self.priority:
                s += self.priority + ws1
            s += self.title
            if self.tags:
                target_col = 79
                #default indentation is 2 per level so add it again
                n = len(s) + 2 * self.level
                ts = enclosed(':'.join(self.tags), ':')
                ns = max(1, target_col - n - len(ts))
                s += ws1 * ns
                s += ts
                #assert(len(s) >= target_col)
            r += [s]
        if self.planning:
            ps = self.planning
            ps = [k + ':' + ws1 + str(v) for k, v in ps.items()]
            r += [ws1.join(ps)]
        if self.properties:
            #todo indent
            ps = drawer('PROPERTIES', [prop(*p) for p in self.properties.items()])
            r.append(ps)

        #r += ['-----']
        r += [dumps(n, indent) for n in self.content]
        #r += ['-----']
        r += [dumps(n) for n in self.children]
        return eol.join(r)

def dumps(ast, indent=''):
    t = type(ast)
    n = t.__name__.lower()

    f = getattr(Writer, n)
    return f(ast, indent)
    
