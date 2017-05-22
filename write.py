from collections import OrderedDict as odict

from str_build import *
from datetime import datetime

from logging import warning
import json

from org.ast import Node as AstNode
import org.ast as ast
import traceback

ORG = 1
JSON = 2

def compose(*funs):
    def do(*args):
        for f in reversed(funs):
            args = (f(*args),)
        return args[0]
    return do

def adder(x):
    return lambda s: x + s

class Org:
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
        start = indent + '#+' + self.start + self.name
        if self.value:
            start += ws1 + self.value
        start += eol
        end = indent + '#+' + self.end + self.name
        return start + self.content + end

    def list(self, indent=''):
        l = map(lambda e: dumps_org(e, indent), self.content)
        r = eol.join(l)
        return r
    

    def listitem(self, indent=''):

        start = self.start() + ws1

        #assert(str(self.content[0])[-1] != eol)
        f = lambda c: dumps_org(c, indent + ws1 * len(start))
        c = dumps_org(self.content[0])
        cs = list(map(f, self.content[1:]))
        cs = [c] + cs
        cs = eol.join(cs)
        
        return indent + start + cs

    orderedlistitem = listitem

    definitionlistitem = listitem


    def table(self, indent=''):

        col_widths = []
        for row in self.content:
            if isinstance(row, ast.TableRow):
                for i, c in enumerate(row.content):
                    n = len(c)
                    if i >= len(col_widths):
                        col_widths.append(n)
                    else:
                        col_widths[i] = max(n, col_widths[i])

        bar = '|'
        plus = '+'
        r = []
        for row in self.content:
            if isinstance(row, ast.TableRow):
                s = indent + bar + bar.join(row.content) + bar
            else:
                l = [n * '-' for n in col_widths]
                s = bar + plus.join(l) + bar
            r.append(s)
        return eol.join(r)

    def drawer(self, indent=''):
        values = list(map(lambda e: dumps_org(e, indent), self.content))
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
        r += [dumps_org(n, indent) for n in self.content]
        #r += ['-----']
        r += [dumps_org(n) for n in self.children]
        return eol.join(r)

class Json:
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
        start = indent + '#+' + self.start + self.name
        if self.value:
            start += ws1 + self.value
        start += eol
        end = indent + '#+' + self.end + self.name
        return start + self.content + end

    def list(self, indent=''):
        l = map(lambda e: dumps_org(e, indent), self.content)
        r = eol.join(l)
        return r
    

    def listitem(self, indent=''):

        start = self.start() + ws1

        #assert(str(self.content[0])[-1] != eol)
        f = lambda c: dumps_org(c, indent + ws1 * len(start))
        c = dumps_org(self.content[0])
        cs = list(map(f, self.content[1:]))
        cs = [c] + cs
        cs = eol.join(cs)
        
        return indent + start + cs

    orderedlistitem = listitem

    definitionlistitem = listitem


    def table(self, indent=''):
        bar = '|'
        r = [indent + bar + bar.join(row.content) + bar for row in self.content]
        return eol.join(r)

    def drawer(self, indent=''):
        values = list(map(lambda e: dumps_org(e, indent), self.content))
        return drawer(self.name, values, indent)
        

    def attr(self, indent=''):
        return indent + '#+' + self.name + ': ' + (self.value or '')

    def node(self, indent):
        attrs = ['level', 'keyword', 'priority', 'title', 'tags', 'planning', 'properties']
        r = odict([(k, getattr(self, k)) for k in attrs])
        r['content'] = [dumps_json(n, indent) for n in self.content]
        r['children'] = [dumps_json(n, indent) for n in self.children]
        return r

def get_type_name(ast):
    return type(ast).__name__.lower()

def _dumps(C, ast, indent=''):
    n = get_type_name(ast)
    f = getattr(C, n)
    return f(ast, indent)

def dumps_org(*args):
    return _dumps(Org, *args)

def _dumps_json(*args):
    return _dumps(Json, *args)

def dumps_json(node, indent=''):
    from marshmallow import Schema, fields

    def serialize_elements(content):
        def serialize(obj):
            if isinstance(obj, str):
                return obj
            n = get_type_name(obj)

            assert(hasattr(schemas, n))
            f = getattr(schemas, n)
            if isinstance(f, Schema):
                c, errs = f.dump(obj)
                assert(not errs)
                
            else:
                try:
                    c = f(obj)
                except Exception as e:
                    print(traceback.format_exc())
                    raise e
            return dict(t=n, c=c)
        return [serialize(o) for o in content]

    serialize_content = lambda node: serialize_elements(node.content)

    class DateTimeOrDateField(fields.DateTime, fields.Date):
        def _serialize(self, value, attr, obj):
            T = fields.DateTime if isinstance(value, datetime) else fields.Date
            return T._serialize(self, value, attr, obj)

    class DateDelta(Schema):
        value = fields.Integer()
        unit = fields.Str()
    class DateShift(Schema):
        kind = fields.Int()
        delta = fields.Nested(DateDelta)
    class DateRepeater(Schema):
        kind = fields.Integer()
        delta = fields.Nested(DateDelta)
        range_delta = fields.Nested(DateDelta)
    class Date(Schema):
        active = fields.Bool()
        date = DateTimeOrDateField()
        end_time = DateTimeOrDateField()
        repeater = fields.Nested(DateRepeater)
        shift = fields.Nested(DateShift)
    class DateRange(Schema):
        start = fields.Nested(Date)
        end = fields.Nested(Date)

    class schemas:
        def para(self):
            return serialize_content(self)

        date = Date()
        daterange = DateRange()

        def attr(obj):
            return { obj.name: obj.value }

        class Drawer(Schema):
            name = fields.Str()
            content = fields.Function(serialize_content)
        drawer = Drawer()

        class Block(Schema):
            start = fields.Str()
            end = fields.Str()
            name = fields.Str()
            value = fields.Str()
            content = fields.Str()
        block = Block()

        def empty(obj):
            return obj.content

        def list(self):
            return serialize_elements(self.content)

        class ListItem(Schema):
            bullet = fields.String()
            content = fields.Function(serialize_content)
        listitem = ListItem()

        class DefinitionListItem(Schema):
            bullet = fields.String()
            tag = fields.String()
            content = fields.Function(serialize_content)
        definitionlistitem = DefinitionListItem()

        class Comment(Schema):
            value = fields.String()
        comment = Comment()


        def table(self):
            return serialize_elements(self.content)

        def tablerow(obj):
            return obj.content
        

    def maybe_daterange(self):
        d = self['date']
        if isinstance(d, ast.DateRange):
            T = schemas.daterange
        else:
            T = schemas.date
        r, errs = T.dump(d)
        assert(not errs)
        return r
            

    def deserialize_content(value):
        pass


    class Planning(Schema):
        name = fields.String()
        date = fields.Function(maybe_daterange)
    plannings = Planning(many=True)

    class Property(Schema):
        name = fields.String()
        value = fields.String()

    class Node(Schema):
        level = fields.Integer()
        keyword = fields.String()
        priority = fields.String()
        title =  fields.String()
        tags = fields.List(fields.Str)
        planning = fields.Function(
            lambda self: plannings.dump(
                [{'name': k, 'date': v} for k, v in self.planning.items()]
            )[0])
        properties = fields.Dict()
        content = fields.Function(serialize_content, deserialize=deserialize_content)
        children = fields.Nested('self', many=True)

        class Meta:
            #fields = ("name", "email", "created_at", "uppername")
            ordered = True
        

    node_schema = Node()
    assert(isinstance(node, AstNode))
    r, errors = node_schema.dump(node)
    assert(not errors)
    #return r
    return json.dumps(r)

_writers = {'org': dumps_org, 'json': dumps_json}

def dumps(ast, indent='', type='org'):
    return _writers[type](ast, indent)
    
