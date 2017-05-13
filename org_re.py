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

def list_parsers():
    return [L_DL, L_UL, L_OL]

def footnote_def_parsers():
    return [L_EMPTY, L_DYNAMIC_BLOCK, L_BLOCK_START, L_SPECIAL_LINE, L_COMMENT, L_DRAWER] + item_parsers() + [L_TEXT]

def item_parsers():
    r = [L_EMPTY, L_HEADLINE, L_DYNAMIC_BLOCK, L_BLOCK_START, L_SPECIAL_LINE, L_FOOTNOTE_DEF, L_COMMENT, L_DRAWER, L_TEXT]
    return r

def greater_parsers():
    r = [L_EMPTY, L_HEADLINE, L_DYNAMIC_BLOCK, L_BLOCK_START, L_SPECIAL_LINE, L_FOOTNOTE_DEF, L_COMMENT, L_DRAWER, L_TEXT]
    return r

def headline_parsers():
    return [L_EMPTY, L_HEADLINE, L_DYNAMIC_BLOCK, L_BLOCK_START, L_SPECIAL_LINE, L_FOOTNOTE_DEF, L_COMMENT, L_DRAWER] + list_parsers() + [L_TEXT]

def greater_block_parsers():
    return headline_parsers()

def drawer_parsers():
    return [L_DRAWER_END, L_EMPTY, L_HEADLINE, L_DYNAMIC_BLOCK, L_BLOCK_START, L_SPECIAL_LINE, L_FOOTNOTE_DEF, L_COMMENT] + list_parsers() + [L_TEXT]

def dynamic_block_parsers():
    return [L_EMPTY, L_TEXT]

#set later
line_types_names = []
line_types = []
parsers = []



# add_parser('empty', ows + eol, empty_parser)
# add_parser('headline', headline_start, headline_parser)
# add_parser('block_start', block_start_start, block_start_parser)
# add_parser('block_end', block_end_start, block_end_parser)
# add_parser('special_line', special_line_start, special_line_parser)
# #todo
# add_parser('comment', comment_start, comment_parser)
# #add_type('comment', comment_start)
# add_parser('drawer_end', drawer_end, drawer_end_parser)
# add_parser('drawer', drawer_start, drawer_parser)
# add_parser('dl', list_format(list_bullet_chars) + g('tag', r'.*') + '::' + g('item', '.*'), dl_parser)
# add_parser('ul', list_format(list_bullet_chars) + g('item', '.*'), ul_parser)
# add_parser('ol', list_format(list_counter) + g('item', '.*'), ol_parser)
# add_parser('text', indent + r'.', text_parser)


def lt_from(ps):
    return [(k, line_types[k]) for k in ps]    

def from_list(ps):
    ts = lt_from(ps)
    ps = dict([(k, parsers[k]) for k in ps])
    return ts, ps

class Parser:
    def __init__(self, parent_parser, it, line_types, parsers, name, continue_predicate=None):
        self.parent_parser = parent_parser
        if parent_parser is None:
            it = QueueFirstIter(it, [])
        self.base_it = it
        def match_type(line):
            #debug([line_types_names[t] for t,r in self.line_types])
            for t, r in self.line_types:
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

        self.line_types = line_types
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

    debug('SUBPARSER HEADLING')
    pred = lambda l: not (_type(l) == L_HEADLINE and get_level(_match(l)) >= level)
    n1 = NTimes(1)
    p = parser.sub_parser(
        *from_list([L_PLANNING, L_PROPERTIES] + headline_parsers())
        , 'headline-planning-properties'
        , lambda l: n1(l) and pred(l)
    )(st)
    n1 = NTimes(1)
    p = parser.sub_parser(
        *from_list([L_PROPERTIES] + headline_parsers())
        , 'headline-properties'
        , lambda l: n1(l) and pred(l)
    )(st)
    p = parser.sub_parser(*from_list(headline_parsers()), 'headline', pred)(st)
    
schedule_item = g('name', '[A-Z]+') + ':' + lax_only(ows, ws) + date_re.simple_date_range
schedule_item_re = re.compile(schedule_item)
schedule_re = re.compile(
    ows +
    n_('[A-Z]+' + ':') + lax(ows, ws) + n_(r'[-+.:<>/[\]A-Za-z0-9\s]')
    + ows + eol
)
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
block_start_token = 'begin_'
block_start_start = indent + special_token + block_start_token
block_end_token = r'end_'
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
    c = [(m.group(k)) for k in ['name', 'value']]

    def inner_text_parser(st, parser, line):
        return _line(line)


    add_parser('block_end', block_end_start, block_end_parser)

    ps = [(L_BLOCK_END, line_types[L_BLOCK_END])
          , (L_TEXT, re.compile(r'.*'))
    ], {
        L_BLOCK_END: block_end_parser
        , L_TEXT: inner_text_parser
    }
    lines = parser.sub_parser(*ps, 'block')(st)

    c += [''.join(lines)]
    r = Block(*c)
    st.current_greater.content.append(r)

def block_end_parser(st, parser, line):
    raise StopIteration()

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
        *from_list(drawer_parsers())
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

    lt, ps = from_list(headline_parsers())
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

def text_parser(st, parser, line):
    clear(st, _match(line).group('indent'))

    text = lambda l: _match(l).group('text')

    def inner_text_parser(st, parser, line):
        return text(line)

    ps = lt_from(headline_parsers()), {L_TEXT: inner_text_parser}
    lines = parser.sub_parser(*ps, 'paragraph')(st)
    lines = [text(line)] + lines
    for l in lines:
        assert(l[-1] != eol)
    r = Para(lines)
    st.current_greater.content.append(r)

def add_parser(name, start, parser):
    line_types.append(start)
    line_types_names.append(name.upper())
    parsers.append(parser)
    
add_parser('empty', ows + eol, empty_parser)
add_parser('headline', headline_start, headline_parser)
add_parser('planning', schedule_re, planning_parser)
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

for i, n in enumerate(line_types_names):
    exec('%s = %s' % ('L_' + n, i))
line_types = [re.compile(v) for v in line_types]


def parse(f):
    st = ParseState()
    Parser(None, f, *from_list(headline_parsers()), 'file')(st)
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
