from re_parse import *

digit = r'[0-9]'
num = digit + '+'
digits = lambda n='+': digit + re_count(n)

time = lambda postfix='': (g('hour' + postfix, digits((1,2))) + ':' + g('minute' + postfix, digits(2)))
time_range = (time() + o('-' + time('_range')))
#dayname = or_('Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun')
#DAYNAME can contain any non whitespace-character besides +, -, ], >, a digit or \n.
dayname = n_(nin_(r'-+\]>\s\d' + '\n'))
duration_chars = r'ymwdh'



n = lambda *args: '_'.join(filter(bool, args))

modifier_duration = lambda name: (
      g(n(name, 'num'), num)
    + g(n(name, 'timespan'), in_(duration_chars))
)

def modifier_duration_range(name):
    rname = n(name, 'range')
    return (
        modifier_duration(name) + o('/' + g(rname, modifier_duration(rname)))
        )

date_modifier = lambda typ, name='': (
    g(n(name, 'type'), typ)
    + modifier_duration(name)
)

date_modifier_range = lambda typ, name='': (
    g(n(name, 'type'), typ)
    + modifier_duration_range(name)
)

repeater_chars = [esc_(s) for s in ['.+', '++', '+']]
def repeater(postfix):
    pf = 'repeater' + postfix
    return g(pf, date_modifier_range(or_(*repeater_chars), pf))

date_shift = lambda postfix: date_modifier(or_('--', '-'), 'shift' + postfix)

date = (g('year', digits(4)) + '-' + g('month', digits(2)) + '-' + g('day', digits(2)))

active = '<', '>'
inactive = r'\[', r'\]'

def date_paren(s, n=''):
    name = '_active%s' % n
    return or_(g(name, r'<'), r'\[') + s + ref_yes_no_(name, '>', r'\]')


def date_stamp(time, extra=(repeater,), postfix=''):
    _g = lambda n, s: g(n + postfix, s)
    #lax: dayname not necessarily optional
    d = _g('date', date) + o(ws + _g('dayname', dayname)) + o(ws + _g('time', time))
    if extra:
        #extra = [o(ws + _g('extra%s' % i, e)) for i, e in enumerate(extra)]
        extra = [o(ws + e(postfix)) for e in extra]
        extra = ''.join(extra)
        d += extra
    return d

full_date_stamp = date_paren(date_stamp(time_range, (repeater, date_shift)))

def date_range(extra=None):
    p = date_paren
    return p(date_stamp(time_range, extra, '_0'), 0) + o('--' + g('daterange', p(date_stamp(time(), extra, '_1'), 1)))


full_date_range = date_range((repeater, date_shift))

simple_date = n_(or_(r'[-+.:/ \d' + duration_chars + ']+', dayname))
simple_date_range = g('date', date_paren(simple_date, 0)) + o('--' + g('daterange', date_paren(simple_date, 1)))


named_date = lambda name, extra=None: (name + ':' + ws + date_range(extra))

#todo closed still stuppports time range etc
closed = named_date('CLOSED', (repeater, date_shift, ))
scheduled = named_date('SCHEDULED', (repeater, date_shift,))
deadlined = named_date('DEADLINE', (repeater, date_shift,))

def named_dates():
    withws = lambda a, b, c: a + ows + b + ows + c
    return ows + or_(
        withws(closed, scheduled, o(deadlined))
        , withws(closed, o(deadlined), o(scheduled))
        , withws(scheduled, deadlined, o(closed))
        , withws(scheduled, o(closed), o(deadlined))
        , withws(deadlined, closed, o(scheduled))
        , withws(deadlined, o(scheduled), o(closed))
        ) + ows


