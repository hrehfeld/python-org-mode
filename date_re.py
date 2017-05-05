from re_parse import *

digit = r'[0-9]'
num = digit + '+'
digits = lambda n='+': digit + re_count(n)

time = lambda postfix='': (g('hour' + postfix, digits(2)) + ':' + g('minute' + postfix, digits(2)))
time_range = (time() + o('-' + time('_range')))
dayname = or_('Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun')
duration_chars = r'ymwd'
date_modifier = lambda typ: (typ + num + in_(duration_chars))

repeater_chars = [esc_(s) for s in ['++', '+']]
repeater = or_(
    date_modifier(or_(*repeater_chars))
    , date_modifier(esc_('.+')) + date_modifier('/')
    )

date_shift = date_modifier(or_(esc_('--'), esc_('-')))

date = (g('year', digits(4)) + '-' + g('month', digits(2)) + '-' + g('day', digits(2)))

active = '<', '>'
inactive = r'\[', r'\]'

def date_paren(s, n=''):
    name = '_active%s' % n
    return or_(g(name, r'<'), r'\[') + s + ref_yes_no_(name, '>', r'\]')


def date_stamp(time, extra=(repeater,), postfix=''):
    _g = lambda n, s: g(n + postfix, s)
    d = _g('date', date) + o(ws + _g('dayname', dayname)) + o(ws + _g('time', time))
    if extra:
        extra = [o(ws + _g('extra%s' % i, e)) for i, e in enumerate(extra)]
        d += ''.join(extra)
    return d

full_date_stamp = date_paren(date_stamp(time_range, (repeater, date_shift)))
print(full_date_stamp)

def date_range(extra=None):
    p = date_paren
    return p(date_stamp(time_range, extra, '_0'), 0) + o('--' + g('daterange', p(date_stamp(time(), extra, '_1'), 1)))


full_date_range = date_range((repeater, date_shift))

simple_date = n_(or_(r'[-+.:/ \d' + duration_chars + ']+', dayname))
simple_date_range = g('date', date_paren(simple_date, 0)) + o('--' + g('daterange', date_paren(simple_date, 1)))
print(simple_date_range)


named_date = lambda name, extra=None: (name + ':' + ws + date_range(extra))

#todo closed still stuppports time range etc
closed = named_date('CLOSED')
scheduled = named_date('SCHEDULED', date_shift)
deadlined = named_date('DEADLINE', date_shift)

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


