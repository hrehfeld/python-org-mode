from collections import OrderedDict as odict
from magic_repr import make_repr

from str_build import *
from datetime import datetime



class Date:
    format = '%Y-%m-%d %a'
    time_format = '%H:%M'
    brackets = { True: ('<', '>'), False: ('[', ']') }

    def __init__(self, active, date, end_time=None):
        self.active = active
        self.date = date
        self.end_time = end_time

    def __str__(self):
        d = self.date.strftime(self.format)
        if isinstance(self.date, datetime):
            d += ws1 + self.date.strftime(self.time_format)
        if self.end_time:
            d += '-' + self.end_time.strftime(self.time_format)
        return enclosed(d, *self.brackets[self.active])

class DateRange:
    def __init__(self, start, end):
        self.start = start
        self.end = end

    def __str__(self):
        return str(self.start) + '--' + str(self.end)

class Text:
    def __init__(self, text):
        self.text = text

    def __str__(self):
        return self.text
        
class Comment(Text):
    def __str__(self):
        r = self.text.split(eol)
        r = ['# ' + l for l in r]
        return eol.join(r)

class Attr():
    def __init__(self, name, value):
        self.name = name
        self.value = value

    def __str__(self):
        return '#+' + self.name + ': ' + (self.value or '')
    
        
class Para:
    def __init__(self, content):
        self.content = content

    def __str__(self):
        return eol.join([str(c) for c in self.content])

class Empty(Para):
    pass

class Block:
    def __init__(self, name, value, content):
        self.name = name
        self.value = value
        self.content = content

    def __str__(self):
        start = '#+begin_' + self.name + ws1 + self.value + eol
        end = '#+end_' + self.name
        return start + self.content + end


class List:
    def __init__(self, indent, items=None):
        self.indent = indent
        self.content = items or []

    def __str__(self):
        return eol.join([self.indent + str(li) for li in self.content])

class ListItem:
    content_str = lambda self: eol.join(map(str, self.content))
    def __init__(self, content=None, bullet='-'):
        self.bullet = bullet
        self.content = content or []

    def __str__(self):
        return self.bullet + ws1 + self.content_str()

class DefinitionListItem(ListItem):
    content_str = lambda self: self.tag + ws1 + '::' + ws1 + ListItem.content_str(self)
    def __init__(self, tag, *args):
        ListItem.__init__(*args)
        self.tag = tag

class OrderedListItem(ListItem):
    pass

class Drawer:
    def __init__(self, name, values):
        self.name = name
        self.values = values

    def __str__(self):
        return drawer(self.name, self.values)
        
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
        
    __repr__= make_repr(
        'level', 'keyword', 'priority', 'title', 'tags', 'planning', 'attrs', 'properties', 'content', 'children',
    )


    def __str__(self):
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
            ps = drawer('PROPERTIES', [prop(*p) for p in self.properties.items()])
            r.append(ps)
            
        r += [str(n) for n in self.content]
        r += [str(n) for n in self.children]
        return eol.join(r)
