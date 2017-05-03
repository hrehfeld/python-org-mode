#!/usr/bin/env python
from pyparsing import Word, alphas, Optional, SkipTo, ZeroOrMore, OneOrMore, Or, CharsNotIn, ParserElement, Group, StringEnd, White
from pyparsing import *

import itertools
import functools

import operator

import sys
from pprint import pprint

#unicodePrintables = ''.join(chr(c) for c in range(sys.maxunicode) 
#                            if not chr(c).isspace())

MAX_DEPTH = 8

def Syntax():
    ParserElement.setDefaultWhitespaceChars('')

    def precise(el):
        g = Group(el)
        g.leaveWhitespace()
        return g

    def lax(el):
        g = Group(el)
        g.setDefaultWhitespaceChars(' \n\t')
        return g

    s = Suppress
    k = Keyword

    ws = s(White())
    iws = White()
    ows = Optional(ws)
    wsl = s(White(' \t'))
    iwsl = (White(' \t'))
    owsl = Optional(wsl)
    eol = s(LineEnd())
    eols = Combine(OneOrMore(eol))
    oeols = Combine(ZeroOrMore(eol))
    sspace = OneOrMore(s(' '))
    maybe_sspace = ZeroOrMore(s(' '))


    enclosed = lambda name, start, end=None: Group(start + name + (start if end is None else end))

    sdash = s('-')
    scolon = s(':')

    def number(n):
        return Word(nums, exact=n)

    special_token = s('#+')
    special_key = Word(alphas + '-_')
    #must end with newline!
    special_value = SkipTo(LineEnd())
    special_attr = Group(
        special_token + special_key + scolon
        + Optional(Optional(special_value)))

    special_attrs = special_attr + eol + ZeroOrMore(special_attr + eol)

    file_special = Group(special_attrs)

    todo_keyword = Literal('TODO') | 'DONE'


    tag_delim = scolon
    tag = SkipTo(tag_delim | eol)
    
    tags = Group(tag_delim + OneOrMore(tag + tag_delim)).leaveWhitespace()

    title = SkipTo((wsl + tags) | LineEnd()) + owsl

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
        return s(start) + Group(d) + s(end)

    def date_range(paren, extra=None):
        return date_stamp(paren, time_range, extra) + Optional('--' + date_stamp(paren, time, extra))

    any_date_range = lambda *args: date_range(inactive, *args) | date_range(active, *args)


    named_date = lambda name, extra=None: Group(name + scolon + wsl + any_date_range(extra)).leaveWhitespace().setName('named_date')

    closed = named_date('CLOSED')
    scheduled = named_date('SCHEDULED', date_shift)
    deadlined = named_date('DEADLINE', date_shift)

    def named_dates():
        return Each([Optional(owsl + d) for d in [closed, scheduled, deadlined]]) + owsl

    drawer_keyword = lambda name: ungroup(enclosed(name, scolon))

    drawer_end = drawer_keyword('END')

    drawer_entry = Group(~drawer_end + drawer_keyword(SkipTo(':') | LineEnd()))

    drawer = lambda name, entries: Group(
        drawer_keyword(name) + eol
        + entries
        + drawer_end + eol)
    

    prop_content = (any_date_range() | restOfLine) + eol
    prop_drawer = drawer('PROPERTIES', dictOf(drawer_entry, prop_content)).setName('prop_drawer')

    logbook_state = ungroup(enclosed(Optional(todo_keyword), s('"')))
    logbook_state_change = s('State') + ws + logbook_state + ws + s('from') + ws + logbook_state

    logbook_content = logbook_state_change | SkipTo(any_date_range()) | restOfLine
    logbook_entry = Group(s('-') + ws + logbook_content + ws + any_date_range())
    logbook_drawer = drawer('LOGBOOK', ZeroOrMore(logbook_entry + eol)).setName('logbook_drawer')

    headline = Forward()




    nested = lambda c, start, end=None: s(start) + c + s(start if end is None else end)
    brackets = lambda *args: nestedExpr('[', ']', *args, ignoreExpr=None)
    brakets = lambda a: ('[') + a + (']')



    link = brackets(
        ungroup(brackets(CharsNotIn('[]')))
        + Optional(ungroup(brackets(CharsNotIn('[]'))))
    ).setName('link')

    
    any_word = Forward().setName('any_word').setDebug()
    def tag(s, e=None):
        r = Group(nested(SkipTo(e or s), s, e))
        return r

    markup = '*/_=~+'
    #TODO
    punctuation = oneOf('. , -')
    word = SkipTo(ws).setName('word')
    def make_any_word(*filter_by):
        any_words = [tag(d) for d in markup] + [any_date_range(), link, word]
        return MatchFirst([Optional(punctuation) + p + Optional(punctuation) for p in any_words if p not in filter_by])
    any_word << make_any_word()
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
    text = (any_word + ZeroOrMore(iws + any_word)).setName('text').setParseAction(join_words)

    para_delim = eol * 2
    para = Group(text) + para_delim
    para.setName('para')


    #todo save parsed key for nested blocks
    special_block_start = special_token + s('begin_') + special_key + Group(Optional(special_value)) + eol
    special_block_end = eol + special_token + s('end') + Optional(s('_' + matchPreviousLiteral(special_key)))
    special_block = Group(special_block_start
                          + SkipTo(special_block_end)
                          + special_block_end
    )

    scheme = Word(alphas)

    #url_chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~/?#[]@!$&\'()*+,;=`.:

    path = Word(alphanums + '/-._~')
    url = Optional(scheme + s('://')) + path

    block_attrs = special_attrs

    block = Optional(block_attrs) + ~(Literal('*') * (1, None) + ws) + (
        special_block | (link + eol) | para.setDebug()
    ) + eol

    content_end = headline | StringEnd()
    content = Group(OneOrMore(block + oeols)).setName('content').setDebug()

    comment = '# ' + restOfLine

    def the_headline(min_depth, top=False):
        nested = ZeroOrMore(the_headline(min_depth + 1)) if min_depth < MAX_DEPTH else empty
        #top level hs may start at nested level
        depth = min_depth if top is False else (min_depth, None)
        r = Group(Combine(Literal('*') * depth) + ws + Optional(todo_keyword + ws)
                  + title
                  + Optional(tags)
                  + eols
                  + Optional(named_dates() + eols)
                  + Optional(prop_drawer + oeols)
                  + Optional(logbook_drawer + oeols)
                  + Optional(content)
                  + nested
        )
        return r

    headline << the_headline(1)

    

    syntax = Optional(file_special) + ZeroOrMore(headline)
    return syntax.leaveWhitespace()

syntax = Syntax()

def parse(s):
    return syntax.parseString(s#, parseAll=True
    )

if __name__ == '__main__':
    with open('/home/hrehfeld/tasks/personal.org', 'r') as f:
    #with open('test.org', 'r') as f:
        ast = parse(f.read())
    pprint(ast.asList())
