#!/usr/bin/env python
from pyparsing import Word, alphas, Optional, SkipTo, ZeroOrMore, OneOrMore, Or, CharsNotIn, ParserElement, Group, StringEnd, White
from pyparsing import *
import pyparsing

import itertools
import functools

import operator

import sys
from pprint import pprint

import re

def unique(l):
    T = type(l)
    r = T()
    for e in l:
        if e not in r:
            r += T(e)
    return r

#unicodePrintables = ''.join(chr(c) for c in range(sys.maxunicode) 
#                            if not chr(c).isspace())

MAX_DEPTH = 8

def _defaultStartDebugAction( instring, loc, expr ): 
    print (("Match " + str(expr) + " at loc " + str(loc) + "(%d,%d)" % ( lineno(loc,instring), col(loc,instring) ))) 
    
def _defaultSuccessDebugAction( instring, startloc, endloc, expr, toks ): 
    print ("Matched " + str(expr) + " -> " + str(toks.asList()) + " at loc " + "(%d,%d)" % ( lineno(startloc,instring), col(startloc,instring) )) 
       
def _defaultExceptionDebugAction( instring, loc, expr, exc ): 
    print ("Exception raised:" + str(exc)) 

saction = nullDebugAction, _defaultSuccessDebugAction, nullDebugAction    

def Syntax():
    comment = '# ' + restOfLine
    ParserElement.setDefaultWhitespaceChars('')
    #ParserElement.enablePackrat()

    def lax(p, strict=None):
        '''support less strict syntax'''
        return p

    def lax_alt(p, strict):
        '''add less strict syntax'''
        return strict | p


    def faster(p):
        '''only for performance'''
        return p

    s = Suppress
    k = Keyword

    def one_of(s):
        return MatchFirst([Literal(t) for t in s])

    def just_chars(cs, n='+'):
        if isinstance(n, int):
            n = '{%s}' % n
        elif isinstance(n, tuple):
            n = '{%s,%s}' % n
        else:
            assert(n in '+*')
        r = '[%s]%s' % (cs, n)
        #print(repr(r))
        return Regex(r)

    eolc = '\n\r'
    wslc = ' \t'
    wsc = ' \t\n\r'
    ws = just_chars(wsc)
    iws = ws
    ows = just_chars(wsc, '*')
    wsl = (just_chars(wslc))
    swsl = s(wsl)
    wsl1 = just_chars(wslc, n=1)
    swsl1 = s(wsl1)
    owsl1 = just_chars(wslc, n=(0,1))
    iwsl = wsl
    owsl = just_chars(wslc, '*')
    eolws = owsl
    eol = (LineEnd())
    eols = just_chars(eolc)
    oeols = just_chars(eolc, '*')

    line = lambda p: LineStart() + p + lax(owsl) + (LineEnd())

    enclosed = lambda name, start, end=None: Group(start + name + (start if end is None else end))

    sdash = s('-')
    scolon = s(':')

    def number(n):
        return Word(nums, exact=n)


    special_block_start_token = s(CaselessLiteral('begin_'))
    special_block_end_token = s(CaselessLiteral('end_'))
    dynamic_block_start_token = s(CaselessLiteral('begin:'))
    dynamic_block_end_token = s(CaselessLiteral('end:'))
    
    special_token = s('#+')
    special_key = ~dynamic_block_start_token + ~dynamic_block_end_token + Word(alphas + '-_', min=1)
    #must end with newline!
    special_value = SkipTo(LineEnd())
    special_attr = Group(
        special_token + faster(~special_block_start_token) + special_key + scolon
        + Optional(Optional(special_value)))

    special_attrs = special_attr + eol + ZeroOrMore(special_attr + eol)

    file_special = Group(special_attrs)

    todo_keyword = Word(alphas.upper()) #Literal('TODO') | 'DONE'


    tag_delim = scolon
    tag = SkipTo(lax_alt(eol, tag_delim))
    
    tags = Group(swsl1 + tag_delim + OneOrMore(tag + tag_delim)).setName('tags')

    title = SkipTo(tags | eol).setName('title')

    priority = enclosed(s('#') + just_chars('A-Z'), s('['), s(']'))

    headline_token = Literal('*')
    headline_start = lambda depth=(1,None): Combine(headline_token * depth) + swsl1
    headline = lambda depth=(1,None): line((
        headline_start(depth)
        + Optional(lax(owsl) + todo_keyword + swsl1)
        + Optional(lax(owsl) + priority + swsl1)
        + title + Optional(tags.copy()))
    ).setName('headline')

    time = Group(number(2) + scolon + number(2))
    time_range = Group(time + Optional(sdash + time))
    dayname = CaselessLiteral('Mon') | 'Tue' | 'Wed' | 'Thu' | 'Fri' | 'Sat' | 'Sun'
    duration = (Literal('y') | 'm' | 'w' | 'd')
    date_modifier = lambda symb: Group(symb + Word(nums).leaveWhitespace() + duration.leaveWhitespace())

    repeater = date_modifier(Literal('++') | '.+' | '+')

    date_shift = date_modifier(Literal('--') | '-')
    
    date_extra = Group(Optional(time_range) + Optional(repeater)
    )

    date = Group(number(4) + sdash + number(2) + sdash + number(2))

    active = '<', '>'
    inactive = '[', ']'
    
    def date_stamp(paren, time, extra=None):
        start, end = paren
        d = date + Optional(wsl + dayname) + Optional(wsl + time) + Optional(wsl + repeater)
        if extra:
            d += Optional(wsl + extra)
        return s(start) + Group(d).setName('date_stamp-inner') + s(end)

    def date_range(paren, extra=None):
        return date_stamp(paren, time_range, extra).setName('date_stamp') + Optional('--' + date_stamp(paren, time, extra))

    any_date_range = lambda *args: (date_range(inactive, *args) | date_range(active, *args)).setName('any_date_range')


    named_date = lambda name, extra=None: Group(name + scolon + wsl + any_date_range(extra)).leaveWhitespace().setName('named_date')

    #todo closed still stuppports time range etc
    closed = named_date('CLOSED')
    scheduled = named_date('SCHEDULED', date_shift)
    deadlined = named_date('DEADLINE', date_shift)

    def named_dates():
        ds = [closed, scheduled, deadlined]
        #ds = itertools.permutations(ds)
        #ds = [Optional(owsl + d) for d in ds]
        #r = [And([dl[0]] + [lax_alt(owsl, wsl) + d for d in dl[1:]]) for dl in ds]
        #return line(owsl + Or(r) + owsl).setName('named_dates')

        o = Optional
        withws = lambda a, b, c: a + owsl + b + owsl + c
        return line(owsl + (
            withws(closed, scheduled, o(deadlined))
            | withws(closed, o(deadlined), o(scheduled)).setName('closed deadline')#.setDebug()
            | withws(scheduled, deadlined, o(closed))
            | withws(scheduled, o(closed), o(deadlined))
            | withws(deadlined, closed, o(scheduled))
            | withws(deadlined, o(scheduled), o(closed))
            ) + owsl).setName('named_dates')


    drawer_token = ':'
    drawer_keyword = lambda name=SkipTo(drawer_token) | lax(LineEnd()): ungroup(enclosed(name, s(drawer_token))) + s(owsl)

    drawer_end = drawer_keyword('END')

    drawer_entry = LineStart() + (~drawer_end + drawer_keyword())

    drawer = lambda name, entries: Group(
        line(lax(owsl) + drawer_keyword(name)).setName('drawer_start: ' + name)#.setDebug()
        + entries
        + line(lax(owsl) + drawer_end))
    

    prop_content = (any_date_range() | restOfLine) + eol
    prop_drawer = drawer('PROPERTIES', dictOf(drawer_entry, prop_content)).setName('prop_drawer')#.setDebug()

    logbook_state = ungroup(enclosed(Optional(todo_keyword), s('"')))
    logbook_entry_state_change = s('State') + wsl + logbook_state + wsl + s('from') + Optional(wsl + logbook_state)
    logbook_entry_refiled = s('Refiled on')
    logbook_entry_modified = s('modified')

    logbook_content = (logbook_entry_state_change | logbook_entry_refiled | logbook_entry_modified) + wsl + any_date_range()
    #TODO restOfLine for logbook OK?
    logbook_entry = LineStart() + Group(s('-') + lax_alt(owsl, wsl) + (logbook_content | restOfLine)) + LineEnd().setName('logbook_entry')#.setDebug() 
    logbook_drawer = drawer('LOGBOOK', lax(oeols) + ZeroOrMore(logbook_entry)).setName('logbook_drawer')

    node = Forward()




    nested = lambda c, start, end=None: s(start) + c + s(start if end is None else end)
    brackets = lambda *args: nestedExpr('[', ']', *args, ignoreExpr=None)
    brakets = lambda a: ('[') + a + (']')



    link = brackets(
        ungroup(brackets(CharsNotIn('[]')))
        + Optional(ungroup(brackets(CharsNotIn('[]'))))
    ).setName('link')

    
    punctuationc = '-,;:"\'/.[](){}<>'
    punctuation = just_chars(punctuationc)
    opunctuation = just_chars(punctuationc, '*')
    inline_markup = '-*/_=~+'
    text_markup = '|' + inline_markup
    line_start_chars = inline_markup + '#\d|:'

    ul_start = owsl + just_chars('-+*', 1)

    lists_start = ul_start
    lists = OneOrMore(Group(line(
        ul_start + owsl1 + owsl + SkipTo(eol)
    )))#.setDebug()


    slurpc = unique((text_markup + punctuationc))
    def for_re_brackets(s):
        r = ''
        e = ''
        for c in s:
            if c == '-':
                e = '-'
            elif c in ']':
                r += '\\' + c
            else:
                r += c
        r = r + e
        return r
    slurpre = '[^\n%s]+' % for_re_brackets(slurpc)
    #print(repr(slurpre))
    slurp = Regex(slurpre).setName('slurp')#.setDebug()#.setDebugActions(*saction)

    word = Regex('\S+').setName('word')#.setDebug()

    word_line = Forward().setName('word_line')
    #nested tags not supported
    # CharsNotIn(e or s, min=1)
    nonnested_tag = lambda s, e=None: Group(
        nested(
            word + OneOrMore(wsl + word)
            , s, e)
    )

    def join_words(tokens):
        r = tokens.copy()
        r.clear()
        last_str = False
        for t in tokens:
            is_r = isinstance(t, ParseResults)
            if not last_str or is_r:
                last_str = not is_r
                r.append(t)
            else:
                r[-1] += t
        return r

    para_illegal_start = headline_start() | special_token | lists_start # | drawer_keyword()

    #TODO
    naive_line = lambda p: (LineStart() + p + LineEnd())#.setDebug().setDebugActions(nullDebugAction, _defaultSuccessDebugAction, nullDebugAction)
    simple_fast_line = (LineStart() + Regex('[^%s\n]*\n' % (line_start_chars))).setName('simple_fast_line')
    #fast_line = naive_line(Regex('[ \t]*[^%s\n][^%s\n]*' % (line_start_chars, inline_markup))).setName('fast_line')
    fast_lines = simple_fast_line
    fast_word = Regex('[^%s\n]+' % (line_start_chars)).setName('fast_word')#.setDebugActions(*saction)
    complex_words = [any_date_range(), link]

    inline_tags = [nonnested_tag(d).setName('Tag %s' % d) for d in inline_markup]

    def words(*filter_by):
        words = complex_words + inline_tags + [word]
        #words = [p for p in words if p not in filter_by]
        #words = [p.setDebugActions(*saction) for p in words]
        #words = [opunctuation + p + opunctuation for p in words]
        #words += [(wsl + punctuation + FollowedBy(wsl)).setName('just_punctuation').setDebugActions(*saction)]
        return ~para_illegal_start + OneOrMore(slurp | MatchFirst(words))

    word_line << (fast_lines
                  | line(words().setName('words inner')).setParseAction(join_words).setName('words')#.setDebug()
    ).setName('word_line')


    text = (OneOrMore(word_line)).setName('text').setParseAction(join_words)#.setDebug()


    para_delim = line(owsl).setName('para_end')
    para = Group(text) + (
        (FollowedBy(para_delim) + para_delim) | FollowedBy(para_illegal_start)
        )
    para.setName('para')#.setDebug()


    #todo save parsed key for nested blocks
    special_block_start = lambda start: line(special_token + lax(owsl) + start + special_key + Group(Optional(special_value))).setName('special_block_start')
    current_special_block_name = matchPreviousLiteral(special_key)
    special_block_end = line(
        special_token + lax(owsl)
        #support #+end only instead of #+end_name
        + lax_alt(s('end'), special_block_end_token + Optional(s(current_special_block_name)))
    ).setName('special_block_end')
    special_block = Group(special_block_start(special_block_start_token)
                          + SkipTo(special_block_end)
                          + special_block_end
    ).setName('special_block')

    current_dynamic_block_name = matchPreviousLiteral(special_key)
    dynamic_block_end = line(special_token + lax(owsl) + dynamic_block_end_token + lax_alt(owsl, wsl) + current_dynamic_block_name).setName('dynamic_block_end')
    dynamic_block = Group(special_block_start(dynamic_block_start_token + wsl)
                          + SkipTo(dynamic_block_end)
                          + dynamic_block_end
    ).setName('dynamic_block')

    scheme = Word(alphas)

    #url_chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~/?#[]@!$&\'()*+,;=`.:

    path = Word(alphanums + '/-._~')
    url = Optional(scheme + s('://')) + path

    block_attrs = special_attrs.copy()
    block_attrs.setName('block_attrs')

    figure = (link + eol).setName('figure')#.setDebug()

    block_delim = line(owsl)
    block_delims = OneOrMore(block_delim)

    #TODO: debug why this is happening
    any_block = ~headline_start() + (
        special_block | dynamic_block | lists | figure | block_delims | para
    ).setName('any_block')
    block = Group(Optional(block_attrs) + any_block).setName('block')

    content = (OneOrMore(block)).setName('content')#.setDebug()


    def the_node(min_depth, top=False):
        nested = ZeroOrMore(the_node(min_depth + 1)) if min_depth < MAX_DEPTH else empty
        r = Group(headline((min_depth, None)) + oeols
                  + Optional(Group(named_dates())) + oeols
                  + Optional(prop_drawer) + oeols
                  + Optional(logbook_drawer) + oeols
                  + Optional(Group(content) + oeols)
#                  + nested + oeols
        )
        return r

    node.setName('node')
    node << the_node(1)

    

    syntax = oeols + Optional(file_special) + ZeroOrMore(node)
    return syntax.leaveWhitespace()

syntax = Syntax()

def parse(s):
    return syntax.parseString(s#, parseAll=True
    )

if __name__ == '__main__':
    from argparse import ArgumentParser

    p = ArgumentParser('orgmode')
    p.add_argument('file')
    p.add_argument('--profile', action='store_true')


    args = p.parse_args()
    filename = args.file
    with open(filename, 'r') as f:
        s = f.read()

    if args.profile:
        import profile
        profile.run('parse(s)', sort='cumtime')
    else:
        import time
        start_time = time.time()
        ast = parse(s)
        duration = time.time() - start_time
        pprint(ast.asList())
        print(duration)
