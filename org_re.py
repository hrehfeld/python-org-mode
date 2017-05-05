#!/usr/bin/env python
import pyparsing
from pprint import pprint
#syntax = ZeroOrMore(LineStart() + (
#        empty_line | headline | special_line | drawer_line | special_block | text
#    ) + restOfLine + LineEnd)

import re, itertools

from collections import OrderedDict as odict

class PeekIter:
    def __init__(self, it):
        self.it = it
        self.queue = []
        
    def __iter__(self):
        return self

    def __next__(self):
        if self.queue:
            return self.queue.pop(0)
        return next(self.it)

    def peek(self):
        if not self.queue:
            self.queue.append(next(self.it))
        return self.queue[0]

    def next_if(self, cond):
        if cond(self.peek()):
            return next(self)
        raise StopIteration

def warning(*args):
    print('WARNING: ', *args)

def debug(*args):
    print('DEBUG: ', *args)

list_format = lambda bullet: r'\s*%s\s' % bullet

enclosed = lambda x, s, e=None: s + x + s if e is None else e

_esc = re.escape
_i = lambda s: r'(?i:%s)' % s
_g = lambda s: r'(?:%s)' % s
_or = lambda *args: _g('|'.join(args))
def re_count(s):
    if isinstance(s, str):
        assert(s in '*+?')
        return s
    elif isinstance(s, int):
        s = s, ''
    return '{%s,%s}' % s
_n = lambda s,n='+': _g(s) + re_count(n)
o = lambda s: _g(s) + '?'
g = lambda n, s: r'(?P<%s>%s)' % (n, s)
def careful(s):
    assert(s[-1] in '+*')
    return _g(s) + '?'

_lax = lambda lax, strict=None: lax if strict is None else _or(strict, lax) 


eol = '\n'
ws_c = '[ \t]'
ws = _n(ws_c, '+')
ows = _n(ws_c, '*')
ws1 = ws_c
ows1 = o(ws_c)

chars = r'\w+'
any = r'.+'


headline_token = r'\*+'
headline_start = headline_token + ws

special_token = r'#\+'
special_start_token = 'begin_'
special_start_start = special_token + special_start_token
special_end_token = r'end_'
special_end_start = special_token + special_end_token

 #(?=begin_)
special_line_start = special_token + g('name', chars) + ':'

comment_start = '#'

drawer_token = r':'
drawer_start = drawer_token + g('name', r'[\w\d]+') + drawer_token
drawer_end = drawer_token + _g(_i('end')) + drawer_token


class ParseState:
    def __init__(self):
        self.headline_level = 0
        self.last_type = None
        self.last_node = None


class Node:
    def __init__(self):
        pass

def take_while(it, cond):
    r = []
    try:
        while cond(it.peek()):
            r.append(next(it))
    except StopIteration:
        pass
    return r
    
def take_while_finish(it, cond, finish):
    r = []
    try:
        while cond(it.peek()):
            r.append(next(it))
        finish(it)
    except StopIteration:
        pass
    return r

ast_types = ['root', 'node', 'drawer', 'comment', 'block', 'attr', 'para', 'text', 'ul', 'ol', 'dl']
for i, v in enumerate(ast_types):
    exec('%s = %s' % (v.upper(), i))
    

        
headline_keyword = r'[A-Z]{3,}'
headline_priority = r'\[#[A-Z]\]'
headline_title = r'.+'
headline_tags = r':.*:'
headline_str = (
    headline_start + ows + o(g('keyword', headline_keyword) + ws)
    + o(g('priority', headline_priority) + ws)
    + careful(headline_title) + ows
    + o(headline_tags + ows)
    + eol
    )
headline_re = re.compile(headline_str)



schedule_item = g('name', _n('[A-Z]+')) + ':' + _lax(ows, ws) + g('date', _n(r'[-+-:<>/[\]A-Za-z0-9\s]') + r'[>\]]')
schedule_item_re = re.compile(schedule_item)
schedule_re = re.compile(
    ows +
    _n('[A-Z]+' + ':') + _lax(ows, ws) + _n(r'[-+-:<>/[\]A-Za-z0-9\s]')
    + ows + eol
)
def headline_parser(st, ast, it, loc, line):

    def parse_schedule():    
        t, i, l = it.peek()
        if not t == L_TEXT:
            return
        if not schedule_re.match(l):
            debug('schedule not matched:', l)
            return
        dates = [m.group('name', 'date') for m in schedule_item_re.finditer(l)]
        print(dates)

            
            
    schedule = parse_schedule()
    m = headline_re.match(line)
    if m:
        #print('M', m.group(0))
        pass
    else:
        print(line)
    content = dict()
    return dict(t=NODE, c=content)
def empty_parser(st, ast, it, loc, line):
    return dict(t=-1, c=dict())

ss_name = chars
ss_value = '[^\n]+'
ss_str = special_start_start + g('name', ss_name) + ows + g('value', o(careful(ss_value))) + ows + eol
print(ss_str)
ss_re = re.compile(ss_str)
def special_start_parser(st, ast, it, loc, line):
    lines = take_while_finish(it
                              , lambda l: l[0] != L_SPECIAL_END
                              #just throw away end marker
                              #TODO: check name
                              , lambda it: next(it))

    lines = ''.join([v for k,i,v in lines])

    m = ss_re.match(line)
    if not m:
        raise Exception(line)
    c = [(m.group(k)) for k in ['name', 'value']] + [lines]
    return dict(t=-1, c=c)
def special_end_parser(st, ast, it, loc, line):
    assert(False)

sa_value = ss_value
sa_str = special_line_start + o(ws1 + ows + g('value', o(careful(sa_value))) + ows) + eol
sa_re = re.compile(sa_str)
def special_line_parser(st, ast, it, loc, line):
    m = sa_re.match(line)
    if not m:
        raise Exception(enclosed(line, '"'))
    print(m.group(0))
    name, value = m.group('name', 'value')
    r = dict(t=ATTR, c={name: value})
    return r
def comment_parser(st, ast, it, loc, line):
    assert(False)

drawer_value = any
drawer_str = drawer_start + g('value', o(ws + drawer_value)) + ows + eol
drawer_re = re.compile(drawer_str)
def drawer_parser(st, ast, it, loc, line):
    lines = take_while_finish(
        it
        , lambda l: l[0] != L_DRAWER_END and l[0] != L_HEADLINE
        #just throw away end marker
        , lambda it: warning('no end marker after %s: %s' % (it.peek()[1], it.peek()[2])) \
        if it.peek()[0] != L_DRAWER_END else next(it)
    )

    m = drawer_re.match(line)
    if not m:
        raise Exception('"%s"' % line)
    name = m.group('name')

    values = lines
    if name == 'PROPERTIES':
        def match(l):
            m = drawer_re.match(l[2])
            if not m:
                warning('no end marker @%s: %s' % (l[1], l[2]))
                return None
            return m.group('name'), m.group('value')
        values = [match(l) for l in lines]
        values = [v for v in values if v is not None]
        values = odict(values)
    r = dict(t=DRAWER, c=[name, values])
    return r
def drawer_end_parser(st, ast, it, loc, line):
    #TODO this should be text then
    raise Exception('Drawer should consume drawer_end @%s: "%s"' % (loc, line))
def dl_parser(st, ast, it, loc, line):
    return dict(t=-1, c=dict())
def ul_parser(st, ast, it, loc, line):
    return dict(t=-1, c=dict())
def ol_parser(st, ast, it, loc, line):
    return dict(t=-1, c=dict())
def text_parser(st, ast, it, loc, line):
    lines = take_while(
        it
        , lambda l: l[0] in {L_TEXT, L_COMMENT}
    )
    lines = [(L_TEXT, line)] + [(t, l) for t, i, l in lines]
    groups = itertools.groupby(lines, lambda l: l[0])
    lines = None
    c = []
    groups = [dict(t=TEXT if t != L_COMMENT else COMMENT, c=''.join([l for t, l in ls])) for t, ls in groups]
            
    r = dict(t=PARA, c=groups)
    return r

line_types = []

parsers = {}

def add_type(name, start):
    t = len(line_types)
    line_types.append((name, start))
    return t
def add_parser(name, start, parser):
    t = add_type(name, start)
    parsers[t] = parser
    
add_parser('empty', r'^\s+$', empty_parser)
add_parser('headline', headline_start, headline_parser)
add_parser('special_start', special_start_start, special_start_parser)
add_parser('special_end', special_end_start, special_end_parser)
add_parser('special_line', special_line_start, special_line_parser)
#todo
#add_parser('comment', comment_start, comment_parser)
add_type('comment', comment_start)
add_parser('drawer_end', drawer_end, drawer_end_parser)
add_parser('drawer', drawer_start, drawer_parser)
add_parser('dl', list_format('[-*+]') + r'.*::', dl_parser)
add_parser('ul', list_format('[-*+]'), ul_parser)
add_parser('ol', list_format('[0-9]+[.)]'), ol_parser)
add_parser('text', r'.', text_parser)

for i, (k, v) in enumerate(line_types):
    exec('%s = %s' % ('L_' + k.upper(), i))
line_types = [(i, re.compile(v)) for i, (k, v) in enumerate(line_types)]


def parse(f):
    ts = []

    def match_type(line):
        for t, r in line_types:
            if r.match(line):
                return t
        assert(False)
        

    line_cont_token = '\\\\\n'
    line_cont_token_len = len(line_cont_token)
    def lines(f):
        it = enumerate(f)
        for i, l in it:
            if l.endswith(line_cont_token):
                oi, ol = next(it)
                l = l[:line_cont_token_len] + ol
                print('hooooooooo', l)
            yield (match_type(l), i, l)
            

    ast = [dict(t=ROOT, c={})]
    st = ParseState()
    it = PeekIter(lines(f))
    try:
        while True:
            e = next(it)
            t, *args = e
            if t in parsers:
                r = parsers[t](st, ast, it, *args)
                ast.append(r)
    except StopIteration:
        pass

    
    #names = [line_types_names[i] for i in ts]
    #return list(zip(names, lines))
    return ast


if __name__ == '__main__':
    from argparse import ArgumentParser

    p = ArgumentParser('orgmode')
    p.add_argument('file')
    p.add_argument('--profile', action='store_true')


    args = p.parse_args()
    filename = args.file
    with open(filename, 'r') as f:
        if args.profile:
            import profile
            profile.run('parse(f)', sort='cumtime')
        else:
            import time
            start_time = time.time()
            ast = parse(f)
            duration = time.time() - start_time
            #pprint(ast)
            print(duration)
