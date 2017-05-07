#!/usr/bin/env python
import pyparsing
from pprint import pprint
#syntax = ZeroOrMore(LineStart() + (
#        empty_line | headline | special_line | drawer_line | special_block | text
#    ) + restOfLine + LineEnd)

import re, itertools

from re_parse import *

from collections import OrderedDict as odict

from magic_repr import make_repr

from ast import *
import ast


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
    print('WARNING:', *args)

def debug(*args):
    print('DEBUG:', *args)

import date_re


_type = lambda l: l[0]
_match = lambda l: l[1]
_loc = lambda l: l[2]
_line = lambda l: l[3]

#set later
line_types_names = {}
parsers = {}
class Parser:
    def get_parser(self, t):
        return parsers[t]
    
    def __call__(self, st, it):
        try:
            while True:
                e = next(it)
                t, *args = e
                p = self.get_parser(t)
                if p is not None:
                    print('calling %s' % line_types_names[t])
                    p(st, it, (t, *args))
        except StopIteration:
            pass

class SubParser:
    def __init__(self, name):
        self.name = name

    def set_stop(self, f):
        self.stop_predicate = f
        return self

    def get_parser(self, t):
        return parsers[t]
    
    def __call__(self, st, it):
        try:
            while self.stop_predicate(it.peek()):
                e = next(it)
                t, *args = e
                p = self.get_parser(t)
                if p is not None:
                    print(self.name + 'calling %s' % line_types_names[t])
                    p(st, it, (t, *args))
                print('stopped at %s' % line_types_names[_type(it.peek())])
        except StopIteration:
            pass
    

class ParseState:
    def __init__(self):
        self.last_type = None
        n = Node(0)
        self.current_nodes = [n]
        self.current_attrs = []
        self.current_greaters = [n]
        self.current_lists = []

    @property
    def current_node(self):
        return self.current_nodes[-1]

    @property
    def current_greater(self):
        return self.current_greaters[-1]

    
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




ast_types = ['root', 'node', 'drawer', 'comment', 'block', 'attr', 'para', 'text', 'ul', 'ol', 'dl', 'date', 'date_range']
for i, v in enumerate(ast_types):
    exec('%s = %s' % (v.upper(), i))

def clear_attrs(st):
    a = st.current_attrs
    st.current_attrs = []
    for k, v in a:
        st.current_node.attrs[k] = v
    a = [Attr(k, v) for k, v in a]
    st.current_node.content.extend(a)

def clear_lists(st, indent):
    while st.current_lists:
        p = st.current_lists[-1]
    a = st.current_attrs
    st.current_attrs = []
    for k, v in a:
        st.current_node.attrs[k] = v
    a = [Attr(k, v) for k, v in a]
    st.current_node.content.extend(a)

def clear(st, indent):
    clear_attrs(st)
    clear_lists(st, indent)

indent = g('indent', ows)    

headline_token = g('level', r'\*+')
headline_start = g('indent', '') + headline_token + lax(ws, ws1)

headline_keyword = r'[A-Z]{3,}'
headline_priority = r'\[#[A-Z]\]'
headline_title = r'.*?'
headline_tags = r':.*:'
headline_str = (
    headline_start + ows + o(g('keyword', headline_keyword) + ws)
    + o(g('priority', headline_priority) + ws)
    + o(g('title', headline_title))
    + o(lax(ows, ws) + g('tags', headline_tags) + ows)
    + eol
    )
headline_re = re.compile(headline_str)
schedule_item = g('name', '[A-Z]+') + ':' + lax_only(ows, ws) + date_re.simple_date_range
schedule_item_re = re.compile(schedule_item)
schedule_re = re.compile(
    ows +
    n_('[A-Z]+' + ':') + lax(ows, ws) + n_(r'[-+.:<>/[\]A-Za-z0-9\s]')
    + ows + eol
)
full_date_re = re.compile(date_re.full_date_stamp)
def make_date(m):
    from datetime import datetime
    from datetime import time
    from datetime import timedelta
    from datetime import date as Date
    
    ms = m.groupdict()

    def parse_date(d):
        dm = full_date_re.match(d)
        if not dm:
            warning('date doesnt match: "' + d + '"')
            return 
        active = dm.group('_active') is not None
        date_t = Date
        date = dm.group('year', 'month', 'day')
        date = [int(d) for d in date]

        hm = 'hour', 'minute'

        end_time = None
        if dm.group('time'):
            t = dm.group(*hm)
            t = [int(e) for e in t]

            et = dm.group('hour_range', 'minute_range')
            if et[0] is not None:
                et = [int(e) for e in et]
                end_time = datetime(*date, *et)
            date = datetime(*date, *t)
        else:
            date = Date(*date)
        return ast.Date(active, date, end_time)

    r = start_date = parse_date(ms['date'])
    end_date = ms['daterange']
    if end_date:
        end_date = parse_date(end_date)
        r = DateRange(start_date, end_date)

    return r

def headline_parser(st, it, line):
    clear(st, 0)
    def parse_schedule():    
        t, m, i, l = it.peek()
        if not t == L_TEXT:
            return
        next(it)
        if not schedule_re.match(l):
            debug('schedule not matched:', l)
            return
        dates = [(m.group('name'), make_date(m)) for m in schedule_item_re.finditer(l)]
        return odict(dates)
    schedule = parse_schedule() or {} #TODO careful, default is unoreded
    m = headline_re.match(_line(line))
    if not m:
        warning('Line doesnt match: ', _line(line))
    level = len(m.group('level'))
    tags = m.group('tags')
    if tags:
        tags = tags.split(':')
        tags = [t for t in tags if t]
    if not tags:
        tags = []
    headline = odict([
        (k, m.group(k)) for k in ['keyword', 'priority', 'title']
    ])
    headline['tags'] = tags
    headline['planning'] = schedule
    #print(headline)

    node = Node(level, **headline)
    p = st.current_nodes[-1]
    while node.level <= st.current_node.level:
        st.current_nodes.pop()
    p = st.current_node
    p.children.append(node)
    st.current_nodes.append(node)
    st.current_greaters = [node]

def empty_parser(st, it, line):
    #empty doesn't clear lists
    clear_attrs(st)

    lines = take_while(it, lambda l: _type(l) == L_EMPTY)
    lines = [_line(line)] + [_line(l) for l in lines]
    lines = [l[:-1] for l in lines]
    st.current_greater.content.append(Empty(lines))

special_token = r'#\+'
special_start_token = 'begin_'
special_start_start = indent + special_token + special_start_token
special_end_token = r'end_'
special_end_start = indent + special_token + special_end_token

        
ss_name = chars
ss_value = '[^\n]+'
ss_str = special_start_start + g('name', ss_name) + ows + g('value', o(careful(ss_value))) + ows + eol
ss_re = re.compile(ss_str)
def special_start_parser(st, it, line):
    clear(st, _match(line).group('indent'))
    lines = take_while_finish(it
                              , lambda l: l[0] != L_SPECIAL_END
                              #just throw away end marker
                              #TODO: check name
                              , lambda it: next(it))

    lines = ''.join([_line(l) for l in lines])
    print(lines)

    m = ss_re.match(_line(line))
    if not m:
        raise Exception(_line(line))
    c = [(m.group(k)) for k in ['name', 'value']] + [lines]
    r = Block(*c)
    st.current_greater.content.append(r)
def special_end_parser(st, it, line):
    raise Exception('special_end should never happen @%s: %s' % (_loc(line), _line(line)))

 #(?=begin_)
special_line_start = indent + special_token + g('name', chars) + ':'

sa_value = ss_value
sa_str = special_line_start + o(ws1 + ows + g('value', o(careful(sa_value))) + ows) + eol
sa_re = re.compile(sa_str)
def special_line_parser(st, it, line):
    m = sa_re.match(_line(line))
    if not m:
        raise Exception(enclosed(_line(line), '"'))
    name, value = m.group('name', 'value')
    st.current_attrs.append((name, value))
    #r = dict(t=ATTR, c={name: value})
    #return r

comment_start = indent + '#' + ws1 + g('text', '.*') + eol

def comment_parser(st, it, line):
    clear(st, _match(line).group('indent'))
    lines = take_while(it, lambda l: _type(l) == L_COMMENT)
    #p = SubParser().set_stop(lambda l: _type(line) != L_COMMENT)(st, it)


    lines = [line] + lines
    lines = [_match(l).group('text') for l in lines]
    lines = eol.join(lines)
    st.current_greater.content.append(Comment(lines))
    
    

drawer_token = r':'
drawer_start = indent + drawer_token + g('name', r'[-_\w\d]+') + drawer_token
drawer_end = indent + drawer_token + i_('end') + drawer_token
    
drawer_value = any
drawer_str = drawer_start + o(lax(ws, ws1) + g('value', drawer_value)) + ows + eol
drawer_re = re.compile(drawer_str)
def drawer_parser(st, it, line):
    print('drawer @ %s' % (_loc(line)))
    clear(st, _match(line).group('indent'))
    lines = take_while_finish(
        it
        , lambda l: _type(l) not in {L_DRAWER_END}
        #just throw away end marker
        , lambda it: warning('expected end marker, found %s at %s: %s' % (
            line_types_names[_type(it.peek())], _loc(it.peek()), _line(it.peek()))) \
        if _type(it.peek()) != L_DRAWER_END else next(it)
    )

    m = drawer_re.match(_line(line))
    if not m:
        raise Exception('"%s"' % _line(line))
    name = m.group('name')

    values = lines
    if name == 'PROPERTIES':
        def match(l):
            m = drawer_re.match(_line(l))
            if not m:
                warning('no end marker @%s: %s' % (_loc(l), _line(l)))
                return None
            return m.group('name'), m.group('value')
        values = [match(l) for l in lines]
        values = [v for v in values if v is not None]
        values = odict(values)
        #todo use union?
        st.current_node.properties = values
    else:
        #TODO handle value types
        values = [_line(l)[:-1] for l in values]
        st.current_node.drawers[name] = values
        st.current_greater.content.append(Drawer(name, values))
def drawer_end_parser(st, it, line):
    #TODO this should be text then
    raise Exception('Drawer should consume drawer_end @%s: "%s"' % (_loc(line), _line(line)))

list_format = lambda bullet: indent + (g('bullet', '%s') % bullet) + r'\s'
list_bullet_chars = '[-*+]'
list_counter = or_('[A-Za-z]', '[0-9]+') + r'[.)]'


ws_re = re.compile(ws)
def dl_parser(st, it, line):
    return dict(t=-1, c=dict())
def ul_parser(st, it, line):

    indent, bullet, item = _match(line).group('indent', 'bullet', 'item')

    p = None
    #check if we're still in the same list
    while isinstance(st.current_greater, List):
        p = st.current_greater
        print(p)
        if p.indent > indent:
            st.current_greaters.pop()
    if p is None or p.indent < indent:
        p = List(indent)
        st.current_greater.content.append(p)
        st.current_greaters.append(p)
    print(repr(p))
        
    class valid_line:
        def __init__(self):
            self.last_ = None

        def __call__(self, l):
            t = _type(l)
            #or two consecutive empty lines
            if self.last_ == L_EMPTY and t == L_EMPTY:
                return False
            self.last_ = t
            #An item ends before the next item,
            if t in {L_UL, L_OL, L_DL}:
                return False
            #the first line less or equally indented than its starting line,

            if t in {L_EMPTY}:
                return True
            try:
                oindent = len(_match(l).group('indent'))
            except IndexError:
                warning('indent redone for ', line_types_names[t])
                m = ws_re.match(_line(l))
                oindent = 0 if m is None else len(m.group())
            if oindent <= len(indent):
                print('indent smaller')
                return False
            return True
    parser = SubParser('ul @%s' % _loc(line)).set_stop(valid_line())

    r = ListItem([item], bullet)
    st.current_greaters.append(r)
    p.content.append(r)

    parser(st, it)

#    item_lines = p(st, it)
#    item_lines = [item] + [_line(l) for l in item_lines]
#    item_lines = ''.join(item_lines)

    #if isinstance(c[-1], List) and c[-1].indent 
        
    #st.current_greaters.pop()

def ol_parser(st, it, line):
    return dict(t=-1, c=dict())
def text_parser(st, it, line):
    clear(st, _match(line).group('indent'))
    lines = take_while(
        it
        , lambda l: _type(l) in {L_TEXT, L_COMMENT}
    )
    lines = [(_type(l), _line(l)) for l in lines]
    lines = [(_type(line), _line(line))] + lines
    groups = itertools.groupby(lines, lambda l: _type(l))
    lines = None
    c = []
    types = {
        L_COMMENT: Comment
        , L_TEXT: Text
        }
    groups = [(types[t])(eol.join([l[:-1] for t, l in ls])) for t, ls in groups]
            
    r = Para(groups)
    st.current_greater.content.append(r)
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
    
add_parser('empty', ows + eol, empty_parser)
add_parser('headline', headline_start, headline_parser)
add_parser('special_start', special_start_start, special_start_parser)
add_parser('special_end', special_end_start, special_end_parser)
add_parser('special_line', special_line_start, special_line_parser)
#todo
add_parser('comment', comment_start, comment_parser)
#add_type('comment', comment_start)
add_parser('drawer_end', drawer_end, drawer_end_parser)
add_parser('drawer', drawer_start, drawer_parser)
add_parser('dl', list_format(list_bullet_chars) + g('tag', r'.*') + '::' + g('item', '.*'), dl_parser)
add_parser('ul', list_format(list_bullet_chars) + g('item', '.*'), ul_parser)
add_parser('ol', list_format(list_counter) + g('item', '.*'), ol_parser)
add_parser('text', indent + r'.', text_parser)

line_types_names = odict([(i, k.upper()) for i, (k, v) in enumerate(line_types)])
for i, (k, v) in enumerate(line_types):
    exec('%s = %s' % ('L_' + k.upper(), i))
line_types = [(i, re.compile(v)) for i, (k, v) in enumerate(line_types)]


def parse(f):
    ts = []

    def match_type(line):
        for t, r in line_types:
            m = r.match(line)
            if m:
                return t, m
        assert(False)
        

    line_cont_token = '\\\\\n'
    line_cont_token_len = len(line_cont_token)
    def lines(f):
        it = enumerate(f)
        for i, l in it:
            if l.endswith(line_cont_token):
                oi, ol = next(it)
                l = l[:line_cont_token_len] + ol
            #print(line_types_names[match_type(l)[0]], i)
            r = (*match_type(l), i, l)
            #print(_line(r)[:-1], line_types_names[_type(r)])
            yield r
            

    ast = [dict(t=ROOT, c={})]
    st = ParseState()
    it = PeekIter(lines(f))

    Parser()(st, it)
    
    #names = [line_types_names[i] for i in ts]
    #return list(zip(names, lines))
    return st.current_nodes[0]


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
            print(ast)
            #print(duration)
