from re_parse import enclosed

eol = '\n'
ws1 = ' '

drawer_key = lambda s: enclosed(s, ':')

def prop(name, value):
    return drawer_key(name) + ws1 + value

def drawer(name, values, indent=''):
    r = [indent + drawer_key(name)] + values + [indent + drawer_key('END')]
    return eol.join(r)

