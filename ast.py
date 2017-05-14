from collections import OrderedDict as odict

from str_build import *
from datetime import datetime, date

def indent(s, indent):
    return eol.join([indent + l for l in s.split(eol)])

def indent_list(s, indent):
    return eol.join([indent + l for l in s])
    

def str_relativetimedelta(d):
    return 

class DateDelta:
    durations = odict(y='years', m='months', w='weeks', d='days', h='hours')

    def __init__(self, value, unit):
        self.value = value
        self.unit = unit

    @classmethod
    def from_org(c, **kwargs):
        value = None
        unit = None
        for k in DateDelta.durations:
            if k in kwargs:
                unit = k
                value = kwargs[k]
                break
        assert(value is not None)
        return c(value, unit)

    def __str__(self):
        r = []
        for k, v in self.durations.items():
            a = getattr(self, v)
            if a != 0:
                r.append(str(a) + k)
        if len(r) != 1:
            raise Exception('malformed datedelta')
        return r[0]


class DateShift:
    ALL = 0
    FIRST = 1
    symbols = ['-', '--']
    types = dict(zip(symbols, [ALL, FIRST]))

    def __init__(self, kind, delta):
        self.kind = kind
        self.delta = delta

    def __str__(self):
        return self.symbols[self.kind] + str(self.delta)

class DateRepeater:
    CUMULATE = 0
    CATCH_UP = 1
    RESTART = 2
    symbols = ['+', '++', '.+']
    types = dict(zip(symbols, [CUMULATE, CATCH_UP, RESTART]))

    def __init__(self, kind, delta, range_delta=None):
        self.kind = kind
        assert(delta is not None)
        self.delta = delta
        self.range_delta = range_delta

    def __str__(self):
        r = self.symbols[self.kind] + str(self.delta)
        if self.range_delta:
            r += '/' + str(self.range_delta)
        return r

class Date:
    format = '%Y-%m-%d %a'
    time_format = '%H:%M'
    brackets = { True: ('<', '>'), False: ('[', ']') }

    def __init__(self, active, _date, end_time=None, repeater=None, shift=None):
        self.active = active
        self.date = _date
        print(repr(_date))
        assert(isinstance(_date, datetime) or isinstance(_date, date))
        self.end_time = end_time
        self.repeater = repeater
        self.shift = shift

    def __str__(self):
        d = self.date.strftime(self.format)
        if isinstance(self.date, datetime):
            d += ws1 + self.date.strftime(self.time_format)
        if self.end_time:
            d += '-' + self.end_time.strftime(self.time_format)
        if self.repeater:
            d += ws1 + str(self.repeater)
        if self.shift:
            d += ws1 + str(self.shift)
        return enclosed(d, *self.brackets[self.active])

class DateRange:
    def __init__(self, start, end):
        self.start = start
        self.end = end

    def __str__(self):
        return str(self.start) + '--' + str(self.end)

class Para:
    def __init__(self, content=None):
        assert(isinstance(content, list))
        self.content = content or []

    def __repr__(self):
        return repr([type(self).__name__, *self.content])

class Empty(Para):
    pass


class Comment:
    def __init__(self, value=None):
        self.value = value or ''
        assert('\n' not in self.value)

    def __repr__(self):
        return repr([type(self).__name__, self.value])
    

class Attr():
    def __init__(self, name, value):
        self.name = name
        self.value = value

    def __repr__(self):
        return repr([type(self).__name__, [self.name, self.value]])
        
class Block:
    def __init__(self, start, end, name, value=None, content=None):
        self.start = start
        self.end = end
        self.name = name
        self.value = value
        self.content = content or ''
        assert(isinstance(self.content, list))

    def __repr__(self):
        return repr([type(self).__name__, [self.name, self.value], *self.content])
    
class CommentBlock(Block):
    def __init__(self, content=None):
        Block.__init__(self, 'comment', None, content)

    def __str__(self, indent=''):
        r = ['# ' + l for l in r]
        return eol.join(r)

class TableRule:
    pass
class TableRow:
    def __init__(self, content=None):
        self.content = content or []

    def __repr__(self):
        return repr([type(self).__name__, self.content])
    
class Table:
    def __init__(self, content=None):
        self.content = content or []

    def __repr__(self):
        return repr([type(self).__name__, self.content])


class List:
    def __init__(self, indent, items=None):
        self.indent = indent
        self.content = items or []


    def __repr__(self):
        return repr([type(self).__name__, self.indent, *self.content])
    

class ListItem:
    start = lambda self: self.bullet

    def __init__(self, content=None, bullet='-'):
        self.bullet = bullet
        self.content = content or []

    def __repr__(self):
        return repr([type(self).__name__, self.bullet, self.content])

class DefinitionListItem(ListItem):
    start = lambda self: self.bullet + ws1 + self.tag + ws1 + '::'

    def __init__(self, tag, *args):
        ListItem.__init__(self, *args)
        self.tag = tag

class OrderedListItem(ListItem):
    pass

class Drawer:
    def __init__(self, name, content=None):
        self.name = name
        self.content = content or []

class Node:
    def __init__(self, level, keyword=None, priority=None, title='', tags=None, attrs=None, content=None, planning=None, properties=None, drawers=None, children=None):
        self.level = level
        self.keyword = keyword
        self.priority = priority
        self.title = title
        self.tags = tags or []
        self.planning = planning or []
        self.properties = properties or odict()
        self.drawers = drawers or odict()
        self.attrs = attrs or odict()
        self.content = content or []
        self.children = children or []
        
#    __repr__= make_repr(
#        'level', 'keyword', 'priority', 'title', 'tags', 'planning', 'attrs', 'properties', 'content', 'children',
#    )


