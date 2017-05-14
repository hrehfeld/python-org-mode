#!/usr/bin/env python3
import pyparsing
from pprint import pprint
#syntax = ZeroOrMore(LineStart() + (
#        empty_line | headline | special_line | drawer_line | special_block | text
#    ) + restOfLine + LineEnd)

import re, itertools

from re_parse import *

from collections import OrderedDict as odict

from ast import *
import ast

import sys

import write

class QueueFirstIter:
    def __init__(self, it, queue):
        self.it = it
        self.queue = queue
        
    def __iter__(self):
        return self

    def __next__(self):
        if self.queue:
            return self.queue.pop(0)
        return next(self.it)

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
    r = 'WARNING:' + ' '.join(map(str, args)) + '\n'
    sys.stderr.write(r)

print_debug = False

def debug(*args):
    if not print_debug:
        return
    r = 'DEBUG:' + ' '.join(map(str, args)) + '\n'
    sys.stderr.write(r)
    pass
    

import date_re


_type = lambda l: l[0]
_match = lambda l: l[1]
_loc = lambda l: l[2]
_line = lambda l: l[3]

build_line= lambda type, match, loc, line: (type, match, loc, line)

class Parsers:
    @staticmethod
    def list():
        return [L_DL, L_UL, L_OL]

    @staticmethod
    def footnote_def():
        return [L_EMPTY, L_DYNAMIC_BLOCK, L_BLOCK_START, L_SPECIAL_LINE, L_COMMENT, L_DRAWER] + Parsers.list_item() + [L_TEXT]

    @staticmethod
    def list_item():
        l = Parsers.list()
        r = filter(lambda e: e not in l, Parsers.all())
        return r

    @staticmethod
    def greater():
        return Parsers.all()

    @staticmethod
    def headline():
        return Parsers.all()

    @staticmethod
    def greater_block():
        return Parsers.all()

    @staticmethod
    def all():
        return [L_EMPTY, L_HEADLINE, L_DYNAMIC_BLOCK, L_BLOCK_START, L_SPECIAL_LINE, L_FOOTNOTE_DEF, L_COMMENT, L_DRAWER, L_TABLE] + Parsers.list() + [L_TEXT]
        

    @staticmethod
    def drawer():
        return [L_DRAWER_END] + Parsers.all()

    @staticmethod
    def dynamic_block():
        return [L_EMPTY, L_TEXT]

#set later
line_types_names = []
line_types = []
parsers = []

def parsers_from_list(types):
    return dict([(k, parsers[k]) for k in types])

def parsers_from_tuples(ps):
    return [(k, t) for k, t, p in ps], dict([(k, p) for k, t, p in ps])

def from_list(types):
    return types, parsers_from_list(types)

def _add_type(name, start):
    line_types.append(start)
    line_types_names.append(name.upper())
    
def add_type(name, start):
    _add_type(name, start)
    parsers.append(None)
    
def add_parser(name, start, parser):
    _add_type(name, start)
    parsers.append(parser)
    


class Parser:
    def __init__(self, parent_parser, it, _line_types, parsers, name, continue_predicate=None):
        self.parent_parser = parent_parser
        if parent_parser is None:
            it = QueueFirstIter(it, [])
        self.base_it = it
        def match_type(line):
            #debug([line_types_names[t] for t,r in self.line_types])
            for t in self.line_types:
                r = line_types[t]
                m = r.match(line)
                if m:
                    debug('from "%s" matched as %s: "%s" to "%s"' % (self.name, line_types_names[t], line[:-1], r))
                    return t, m
            raise Exception('Unmatched "%s": in %s' % (line, self.line_types))

        #TODO: would need backwards regex check for \\ + ows
        line_cont_token = '\\\\\n'
        line_cont_token_len = len(line_cont_token)
        def lines(f):
            it = enumerate(f)
            for i, l in it:
                if l.endswith(line_cont_token):
                    oi, ol = next(it)
                    l = l[:-line_cont_token_len] + ol
                #print(line_types_names[match_type(l)[0]], i)
                r = (*match_type(l), i, l)
                #print(_line(r)[:-1], line_types_names[_type(r)])
                yield r

        self.it = PeekIter(lines(it))

        assert(_line_types is not None)
        self.line_types = _line_types
        assert(isinstance(parsers, dict))
        self.parsers = parsers
        self.name = name
        self.continue_predicate = continue_predicate or (lambda *args: True)

    def __call__(self, st, *args):
        it = self.it
        r = []
        try:
            while self.continue_predicate(it.peek()):
                t = _type(it.peek())
                if t not in self.parsers:
                    debug('%s not in self.parsers: %s' % (line_types_names[t], self.parsers))
                    raise StopIteration()
                l = next(it)
                p = self.parsers[t]
                debug('from "%s" calling %s %s' % (self.name, line_types_names[t], p))
                r.append(p(st, self, l, *args))
            debug('StopPredicate at %s' % line_types_names[_type(it.peek())])
        except StopIteration:
            debug('StopIteration')
        self.reset_state()
        return r

    def reset_state(self):
        #reset inner it state
        #debug(self.it.queue)
        #debug(self.base_it.queue)
        self.base_it.queue.extend([_line(l) for l in self.it.queue])
        self.it.queue = []

    def sub_parser(self, *args):
        self.reset_state()
        return Parser(self, self.base_it, *args)

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

def noop_parser(st, parser, line):
    pass
    

indent = g('indent', careful(ows))
no_indent = g('indent', '')

headline_token = g('level', r'\*+')
headline_start = no_indent + headline_token + lax(ws, ws1)

headline_keyword = r'[A-Z]{3,}'
headline_priority = r'\[#[A-Z]\]'
headline_title = r'.*?'
# TAGS is made of words containing any alpha-numeric character, underscore, at sign, hash sign or percent sign, and separated with colons.
headline_tags = enclosed(r'[:%#@_\w]', ':', ':')
headline_str = (
    headline_start + ows + o(g('keyword', headline_keyword) + ws)
    + o(g('priority', headline_priority) + ws)
    + o(g('title', headline_title))
    + o(lax(ows, ws) + g('tags', headline_tags) + ows)
    + eol
    )
headline_re = re.compile(headline_str)
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
            warning('re', date_re.full_date_stamp)

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

        def get_modifier_delta(m, p):
            r = m.group(*[p + '_' + s for s in ['num', 'timespan']])
            
            v = int(r[0])

            k = r[1]
            d = DateDelta.from_org(**{k: v})
            return d

        def get_modifier(m, p):
            r = m.group(p + '_' + 'type')
            return (r, get_modifier_delta(m, p))


        m = dm.groupdict()

        def guess_key(key, ks):
            for k in ks:
                m = re.match(g('key', key + num) + '$', k)
                if m and ks[k] is not None:
                    #get number e.g. -> 'repeater0'
                    key = m.group('key')
                    break
            return key

        repeater_key = guess_key('repeater', m)
        shift_key = guess_key('shift', m)
        
        #debug(m, repeater_key, shift_key)

        repeater = m.get(repeater_key, None)
        if repeater:
            repeater = get_modifier(dm, repeater_key)


            repeater_range = m.get(repeater_key + '_range', None)
            if repeater_range:
                repeater_range = get_modifier_delta(dm, repeater_key + '_range')

            repeater = DateRepeater(
                DateRepeater.types[repeater[0]]
                , *repeater[1:]
                , repeater_range
            )

        shift = m.get(shift_key, None)
        if shift:
            shift = get_modifier(dm, shift_key)
            shift = DateShift(DateShift.types[shift[0]], *shift[1:])

        return ast.Date(active, date, end_time, repeater=repeater, shift=shift)

    r = start_date = parse_date(ms['date'])
    assert(r)
    end_date = ms['daterange']
    if end_date:
        end_date = parse_date(end_date)
        assert(end_date)
        r = DateRange(start_date, end_date)

    return r

def headline_parser(st, parser, line):
    debug('-------HEADLINE')
    clear(st, 0)

    m = headline_re.match(_line(line))
    if not m:
        warning('Line doesnt match: ', _line(line))

    get_level = lambda m: len(m.group('level'))
    level = get_level(m)
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

    node = Node(level, **headline)
    
    p = st.current_nodes[-1]
    while node.level <= st.current_node.level:
        st.current_nodes.pop()
    p = st.current_node
    p.children.append(node)
    st.current_nodes.append(node)
    st.current_greaters.append(node)

    class NTimes:
        def __init__(self, n):
            self.n = n
            self.i = 0
        def __call__(self, *args):
            self.i += 1
            return self.i <= self.n

    p = parser.sub_parser(
        [L_PLANNING, L_PROPERTIES] + Parsers.headline()
        , {L_PLANNING: planning_parser}
        , 'headline-planning'
        , NTimes(1)
    )(st)
    p = parser.sub_parser(
        [L_PROPERTIES] + Parsers.headline()
        , {L_PROPERTIES: properties_parser}
        , 'headline-properties'
        , NTimes(1)
    )(st)

    pred = lambda l: not (_type(l) == L_HEADLINE and get_level(_match(l)) >= level)
    p = parser.sub_parser(
        Parsers.headline()
        , parsers_from_list(Parsers.headline())
        , 'headline'
        , pred
    )(st)
    
schedule_item = g('name', '[A-Z]+') + ':' + lax_only(ows, ws) + date_re.simple_date_range
schedule_item_re = re.compile(schedule_item)
schedule_re_str = (
    ows +
    n_('[A-Z]+' + ':') + lax(ows, ws) + n_(r'[-+.:<>/[\]A-Za-z0-9\s]')
    + ows + eol
)
schedule_re = re.compile(schedule_re_str)
def planning_parser(st, parser, line):
    m = _match(line)
    dates = odict([(m.group('name'), make_date(m)) for m in schedule_item_re.finditer(_line(line))])
    debug(dates)
    st.current_node.planning = dates

def empty_parser(st, parser, line):
    #empty doesn't clear lists
    clear_attrs(st)

    c = st.current_greater.content
    c.append(Empty([_line(line)[:-1]]))

special_token = r'#\+'
block_start_token = g('start_token', i_('begin_'))
block_start_start = indent + special_token + block_start_token
block_end_token = g('end_token', i_('end_'))
block_end_start = indent + special_token + block_end_token

        
block_start_name = chars
block_start_value = '[^\n]+'
block_start_str = block_start_start + g('name', block_start_name) + ows + g('value', o(careful(block_start_value))) + ows + eol
block_start_re = re.compile(block_start_str)
def block_start_parser(st, parser, line):
    clear(st, _match(line).group('indent'))

    m = block_start_re.match(_line(line))
    if not m:
        raise Exception(_line(line))


    end_case = None
    def block_end_parser(st, parser, line):
        nonlocal end_case
        end_case = _match(line).group('end_token')
        raise StopIteration()

    ts = [L_BLOCK_END, L_BLOCK_CONTENT, L_HEADLINE]
    ps = dict(zip(ts, [block_end_parser, block_content_parser]))
    debug(ps)
    lines = parser.sub_parser(
        ts
        , ps
        , 'block'
    )(st)
    if not end_case:
        warning('no end tag for block at %s' % (_loc(line)))
        assert(False)
        #end_case = 'begin_'

    c = [m.group('start_token'), end_case]
    c += [(m.group(k)) for k in ['name', 'value']]
    c += [''.join(lines)]
    r = Block(*c)
    st.current_greater.content.append(r)

def block_end_parser(st, parser, line):
    raise StopIteration()

def block_content_parser(st, parser, line):
    return _line(line)


 #(?=begin_)
special_line_start = indent + special_token + g('name', chars) + ':'

special_line_value = block_start_value
special_line_str = special_line_start + o(ws1 + ows + g('value', o(careful(special_line_value))) + ows) + eol
special_line_re = re.compile(special_line_str)
def special_line_parser(st, parser, line):
    m = special_line_re.match(_line(line))
    if not m:
        raise Exception(enclosed(_line(line), '"'))
    name, value = m.group('name', 'value')
    #TODO check for different types of attrs
    st.current_attrs.append((name, value))

dynamic_block_start_token = i_('begin')
dynamic_block_start = indent + special_token + block_start_token + ':' + ws + g('name', nws
) + lax(ws, ws1) + g('parameters', any) + eol

comment_start = indent + '#' + ws1 + g('text', '.*') + eol

def comment_parser(st, parser, line):
    m = _match(line)
    clear(st, m.group('indent'))
    text = m.group('text')

    r = Comment(text)
    st.current_greater.content.append(r)

drawer_token = r':'
drawer_value = g('value', nin_(eol) + '+')

properties_name = i_('PROPERTIES')
properties_start = indent + drawer_token + properties_name + drawer_token
properties_property = indent + drawer_token + g('name', r'\S+') + o(g('append', r'\+')) + drawer_token + o(ws1 + drawer_value) + eol
def properties_parser(st, parser, line):
    clear(st, _match(line).group('indent'))

    p = parser.sub_parser(*from_list([L_DRAWER_END, L_PROPERTY]), 'PROPERTIES')(st)

def property_parser(st, parser, line):
    m = _match(line)
    #TODO parse attr properties
    #TODO parse append
    k, v = m.group('name'), m.group('value')
    st.current_node.properties[k] = v
    

drawer_start = indent + drawer_token + g('name', # not_(properties_name) + 
                                         r'[-_\w\d]+') + drawer_token + ows + eol
drawer_end = indent + drawer_token + i_('end') + drawer_token
    
drawer_re = re.compile(drawer_start)
def drawer_parser(st, parser, line):
    #print('drawer @ %s' % (_loc(line)))
    clear(st, _match(line).group('indent'))
    m = drawer_re.match(_line(line))
    if not m:
        raise Exception('"%s"' % _line(line))
    name = m.group('name')

    
    r = Drawer(name)
    st.current_node.drawers[name] = r
    st.current_greater.content.append(r)
    st.current_greaters.append(r)
    parser.sub_parser(
        *from_list(Parsers.drawer())
        , 'drawer'
        , lambda l: _type(l) not in {L_HEADLINE}
    )(st)
    st.current_greaters.pop()

def drawer_end_parser(st, parser, line):
    #throw away
    raise StopIteration()



footnote_def_start = no_indent + enclosed(or_(num, 'fn:' + g('label', r'[-_\w]+')), r'\[', r'\]') + g('contents', any) + eol

list_format = lambda bullet: indent + (g('bullet', '%s') % bullet) + r'\s'
list_bullet_chars = '[-*+]'
list_counter = or_('[A-Za-z]', '[0-9]+') + r'[.)]'


ws_re = re.compile(ws)
def li_parser(st, parser, line, li):
    indent = _match(line).group('indent')
    nindent = len(indent)

    p = None
    #check if we're still in the same list
    while isinstance(st.current_greater, List):
        p = st.current_greater
        debug(repr(p))
        if p.indent > indent:
            st.current_greaters.pop()
        else:
            break
    if p is None or p.indent < indent:
        p = List(indent)
        st.current_greater.content.append(p)
        st.current_greaters.append(p)
    #print(repr(p))

    list_end = False
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
            #if t in {L_UL, L_OL, L_DL}:
            #    return False

            #the first line less or equally indented than its starting
            #line that is not empty
            if t in {L_EMPTY}:
                return True
            try:
                oindent = len(_match(l).group('indent'))
            except IndexError:
                warning('indent redone for ', line_types_names[t])
                m = ws_re.match(_line(l))
                oindent = 0 if m is None else len(m.group())
            if oindent <= nindent:
                nonlocal list_end
                assert(not list_end)
                list_end = True
                return False
            return True

    p.content.append(li)
    st.current_greaters.append(li)

    lt, ps = from_list(Parsers.headline())
    parser.sub_parser(lt, ps, 'ul @%s' % _loc(line), valid_line())(st)

    st.current_greaters.pop()
    if list_end:
        st.current_greaters.pop()

def dl_parser(st, parser, line):
    indent, bullet, tag, item = _match(line).group('indent', 'bullet', 'tag', 'item')
    if item:
        assert(item[-1] != eol)
    li = DefinitionListItem(tag, [Para([item])], bullet)
    li_parser(st, parser, line, li)

def ul_parser(st, parser, line):
    indent, bullet, item = _match(line).group('indent', 'bullet', 'item')
    if item:
        assert(item[-1] != eol)
    li = ListItem([Para([item])], bullet)

    li_parser(st, parser, line, li)

def ol_parser(st, parser, line):
    indent, bullet, item = _match(line).group('indent', 'bullet', 'item')
    if item:
        assert(item[-1] != eol)
    li = OrderedListItem([Para([item])], bullet)

    li_parser(st, parser, line, li)

bar = r'\|'
table_cell_inside = r'[^|\n]+' + ows
table_cell = g('text', table_cell_inside) + bar
table_cell_at_eol = g('text_eol', table_cell_inside) + o(bar)

table_cell_re = re.compile(table_cell)
table_cell_at_eol_re = re.compile(table_cell_at_eol)

table_start = indent + bar
table_row_start = table_start + or_(n_(table_cell) + o(table_cell_at_eol), g('is_rule', r'\-'))

table_row_start_re = re.compile(table_row_start)

def table_parser(st, parser, line):
    
    r = Table()
    def table_row_parser(st, parser, line):
        is_rule = m.group('is_rule')
        if is_rule:
            row = TableRule()
        else:
            cs = []
            for c in table_cell_re.finditer(_line(line)):
                cs.append(c.group('text'))
                debug(c.group())
            rest = _line(line)
            if c:
                rest = _line(line)[c.end():]
            c = table_cell_at_eol_re.match(rest)
            if c:
                debug(c.group())
                cs.append(c.group('text_eol'))
                
            row = TableRow(cs)
        r.content.append(row)

    m = table_row_start_re.match(_line(line))
    assert(m)
    table_row_parser(st, parser, build_line(L_TABLE_ROW, m, _loc(line), _line(line)))

    ts = [L_TABLE_ROW] + Parsers.all()
    ts.remove(L_TABLE)
    lines = parser.sub_parser(
        ts
        , dict([(L_TABLE_ROW, table_row_parser)])
        , 'table')(st)

    st.current_greater.content.append(r)

add_parser('table', table_start, table_parser)
add_type('table_row', table_start)

def text_parser(st, parser, line):
    clear(st, _match(line).group('indent'))

    text = lambda l: _match(l).group('text')

    def inner_text_parser(st, parser, line):
        return text(line)

    ps = Parsers.headline(), {L_TEXT: inner_text_parser}
    lines = parser.sub_parser(*ps, 'paragraph')(st)
    lines = [text(line)] + lines
    for l in lines:
        assert(l[-1] != eol)
    r = Para(lines)
    st.current_greater.content.append(r)

add_parser('empty', ows + eol, empty_parser)
add_parser('headline', headline_start, headline_parser)
add_parser('planning', schedule_re_str, planning_parser)
add_parser('properties', properties_start, properties_parser)
add_parser('property', properties_property, property_parser)
add_parser('block_start', block_start_start, block_start_parser)
add_parser('block_end', block_end_start, block_end_parser)
add_parser('special_line', special_line_start, special_line_parser)
add_parser('dynamic_block', dynamic_block_start, noop_parser)
add_parser('comment', comment_start, comment_parser)
add_parser('drawer_end', drawer_end, drawer_end_parser)
add_parser('drawer', drawer_start, drawer_parser)
add_parser('footnote_def', footnote_def_start, noop_parser)
add_parser('dl', list_format(list_bullet_chars) + g('tag', r'.*') + ws1 + '::' + ws1 + g('item', '.*') + eol, dl_parser)
add_parser('ul', list_format(list_bullet_chars) + g('item', '.*') + eol, ul_parser)
add_parser('ol', list_format(list_counter) + g('item', '.*') + eol, ol_parser)
add_parser('text', indent + g('text', r'.+') + eol, text_parser)

add_parser('block_content', r'.*', block_content_parser)


for i, n in enumerate(line_types_names):
    exec('%s = %s' % ('L_' + n, i))
line_types = [re.compile(v) for v in line_types]


def parse(f):
    st = ParseState()
    Parser(None, f, *from_list(Parsers.headline()), 'file')(st)
    return st.current_nodes[0]


if __name__ == '__main__':
    from argparse import ArgumentParser

    p = ArgumentParser('orgmode')
    p.add_argument('file')
    p.add_argument('--profile', action='store_true')
    p.add_argument('--verbose', '-v', action='store_true')

    args = p.parse_args()

    if args.verbose:
        print_debug = True
    

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
            print(write.dumps(ast))
            #print(repr(ast))
            #print(duration)
