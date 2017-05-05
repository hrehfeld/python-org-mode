#!/usr/bin/env python
import pyparsing
from pprint import pprint
#syntax = ZeroOrMore(LineStart() + (
#        empty_line | headline | special_line | drawer_line | special_block | text
#    ) + restOfLine + LineEnd)

import re

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

list_format = lambda bullet: r'\s*%s\s' % bullet

_i = lambda s: r'(?i:%s)' % s
_g = lambda s: r'(?:%s)' % s
o = lambda s: _g(s) + '?'
g = lambda n, s: r'(?P<%s>%s)' % (n, s)
def careful(s):
    assert(s[-1] in '+*')
    return _g(s) + '?'
eol = '$'
ws = r'\s+'
ows = r'\s*'
ws1 = r'\s+'
ows1 = r'\s*'

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
special_line_start = special_token + chars + ':'

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
def headline_parser(st, ast, it, loc, line):
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

def take_while_finish(it, cond, finish):
    r = []
    try:
        while cond(it.peek()):
            r.append(next(it))
        finish(it)
    except StopIteration:
        pass
    return r
    

ss_name = chars
ss_value = '.+'
ss_str = special_start_start + g('name', ss_name) + ows + g('value', o(careful(ss_value))) + ows + eol
print(ss_str)
ss_re = re.compile(ss_str)
def special_start_parser(st, ast, it, loc, line):

    lines = take_while_finish(it
                              , lambda l: l[0] != L_SPECIAL_END
                              #just throw away end marker
                              #TODO: check name
                              , lambda it: next(it))

    # lines = []
    # try:
    #     while it.peek()[0] != L_SPECIAL_END:
    #         lines.append(next(it)[1])
    #     #just throw away end
    #     end = next(it) 
    # except StopIteration:
    #     pass

    lines = ''.join([v for k,i,v in lines])

    m = ss_re.match(line)
    if not m:
        raise Exception(line)
    c = [(m.group(k)) for k in ['name', 'value']] + [lines]
    return dict(t=-1, c=c)
def special_end_parser(st, ast, it, loc, line):
    assert(False)
def special_line_parser(st, ast, it, loc, line):
    return dict(t=-1, c=dict())
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
    print(r)
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
    return dict(t=-1, c=dict())

line_types = []

parsers = {}

def add_parser(name, start, parser):
    t = len(line_types)
    line_types.append((name, start))
    parsers[t] = parser
    
add_parser('empty', r'^\s+$', empty_parser)
add_parser('headline', headline_start, headline_parser)
add_parser('special_start', special_start_start, special_start_parser)
add_parser('special_end', special_end_start, special_end_parser)
add_parser('special_line', special_line_start, special_line_parser)
add_parser('comment', comment_start, comment_parser)
add_parser('drawer_end', drawer_end, drawer_end_parser)
add_parser('drawer', drawer_start, drawer_parser)
add_parser('dl', list_format('[-*+]') + r'.*::', dl_parser)
add_parser('ul', list_format('[-*+]'), ul_parser)
add_parser('ol', list_format('[0-9]+[.)]'), ol_parser)
add_parser('text', r'.', text_parser)

for i, (k, v) in enumerate(line_types):
    exec('%s = %s' % ('L_' + k.upper(), i))
line_types = [(i, re.compile(v)) for i, (k, v) in enumerate(line_types)]

ast_types = ['root', 'node', 'drawer', 'block', 'attr', 'para', 'ul', 'ol', 'dl']
for i, v in enumerate(ast_types):
    exec('%s = %s' % (v.upper(), i))
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
