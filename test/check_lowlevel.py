# Copyright ReportLab Europe Ltd. 2000-2015
# see license.txt for license details

# Tests of various functions and algorithms in preppy.
# no side-effects on file system, run anywhere.
__version__=''' $Id$ '''
import sys, os, glob, string, re
import preppy
import unittest
isPy3 = sys.version_info[0]==3
if isPy3:
    xrange = range
isPy34 = isPy3 and sys.version_info[1]>=4
isPy35 = isPy3 and sys.version_info[1]>=5
isPy38 = isPy3 and sys.version_info[1]>=8

def P__tokenize(source,filename='<unknown>'):
    P=preppy.PreppyParser(source,filename)
    return P._PreppyParser__tokenize()

def P__preppy(source,filename='<unknown>'):
    P=preppy.PreppyParser(source,filename)
    P._PreppyParser__tokenize()
    return P.dump(P._PreppyParser__preppy())

class PreppyParserTestCase(unittest.TestCase):
    '''test the preppy parser class'''

    def __init__(self,*args,**kwds):
        unittest.TestCase.__init__(self,*args,**kwds)
        self.maxDiff = None

    @staticmethod
    def fixup(s):
        sNN = ' None, None,'
        if isPy3:
            sTE = 'Try'
            sTFL = ' [],'
            if isPy35: sNN = ''
        else:
            sTE = 'TryExcept'
            sTFL = ''
        return s.replace('sTE',sTE).replace('sTFL',sTFL).replace('sNN',sNN)

    def assertEqualStr(self,a,b):
        b = self.fixup(b)
        for i in xrange(max(len(a),len(b))):
            if a[i:i+1]!=b[i:i+1]:
                raise ValueError('Not Equal\n%r !!!!! %r\n%r !!!!! %r' % (a[:i],a[i:],b[:i],b[i:]))

    def checkTokenize(self):
        Token = preppy.Token
        self.assertEqual(P__tokenize('Hello World!'),[('const', 0, 12), ('eof', 12, 12)])
        self.assertEqual(P__tokenize('{{1}}'),[('expr', 2, 3), ('eof', 5, 5)])
        self.assertEqual(P__tokenize('{{while 1}}'),[Token(kind='while', start=2, end=9), Token(kind='eof', start=11, end=11)])
        self.assertEqual(P__tokenize('{{for i in 1,2}}'),[Token(kind='for', start=2, end=14), Token(kind='eof', start=16, end=16)])
        self.assertEqual(P__tokenize('{{if 1}}'), [Token(kind='if', start=2, end=6), Token(kind='eof', start=8, end=8)])
        self.assertEqual(P__tokenize('{{script}}a=2{{endscript}}'),[('script', 2, 8), ('const', 10, 13), ('endscript', 15, 24), ('eof', 26, 26)])
        self.assertEqual(P__tokenize('{{script}}a=1\nb=2\nc=3{{endscript}}'), [Token(kind='script', start=2, end=8), Token(kind='const', start=10, end=21), Token(kind='endscript', start=23, end=32), Token(kind='eof', start=34, end=34)])

    if isPy38:
        results=dict(
                check_break="[For(Name('i', Store(), lineno=1, col_offset=6, end_lineno=1, end_col_offset=21), Tuple([Constant(1, None, lineno=1, col_offset=11, end_lineno=1, end_col_offset=26), Constant(2, None, lineno=1, col_offset=13, end_lineno=1, end_col_offset=28), Constant(3, None, lineno=1, col_offset=15, end_lineno=1, end_col_offset=30)], Load(), lineno=1, col_offset=11, end_lineno=1, end_col_offset=30), [Expr(Call(Name('__write__', Load(), lineno=1, col_offset=18, end_lineno=1, end_col_offset=24), [Constant('abcdef', lineno=1, col_offset=18, end_lineno=1, end_col_offset=24)], [], lineno=1, col_offset=18, end_lineno=1, end_col_offset=24), lineno=1, col_offset=18, end_lineno=1, end_col_offset=24), If(Compare(Name('i', Load(), lineno=1, col_offset=29, end_lineno=1, end_col_offset=37), [Eq()], [Constant(3, None, lineno=1, col_offset=32, end_lineno=1, end_col_offset=40)], lineno=1, col_offset=29, end_lineno=1, end_col_offset=40), [Break( lineno=1, col_offset=37, end_lineno=1, end_col_offset=42)], [], lineno=1, col_offset=26, end_lineno=1, end_col_offset=51)], [Expr(Call(Name('__write__', Load(), lineno=1, col_offset=61, end_lineno=1, end_col_offset=66), [Constant('eeeee', lineno=1, col_offset=61, end_lineno=1, end_col_offset=66)], [], lineno=1, col_offset=61, end_lineno=1, end_col_offset=66), lineno=1, col_offset=61, end_lineno=1, end_col_offset=66)], None, lineno=1, col_offset=2, end_lineno=1, end_col_offset=74)]",
                check_continue="[For(Name('i', Store(), lineno=1, col_offset=6, end_lineno=1, end_col_offset=21), Tuple([Constant(1, None, lineno=1, col_offset=11, end_lineno=1, end_col_offset=26), Constant(2, None, lineno=1, col_offset=13, end_lineno=1, end_col_offset=28), Constant(3, None, lineno=1, col_offset=15, end_lineno=1, end_col_offset=30)], Load(), lineno=1, col_offset=11, end_lineno=1, end_col_offset=30), [Expr(Call(Name('__write__', Load(), lineno=1, col_offset=18, end_lineno=1, end_col_offset=24), [Constant('abcdef', lineno=1, col_offset=18, end_lineno=1, end_col_offset=24)], [], lineno=1, col_offset=18, end_lineno=1, end_col_offset=24), lineno=1, col_offset=18, end_lineno=1, end_col_offset=24), If(Compare(Name('i', Load(), lineno=1, col_offset=29, end_lineno=1, end_col_offset=37), [Eq()], [Constant(3, None, lineno=1, col_offset=32, end_lineno=1, end_col_offset=40)], lineno=1, col_offset=29, end_lineno=1, end_col_offset=40), [Continue( lineno=1, col_offset=37, end_lineno=1, end_col_offset=45)], [], lineno=1, col_offset=26, end_lineno=1, end_col_offset=54)], [Expr(Call(Name('__write__', Load(), lineno=1, col_offset=64, end_lineno=1, end_col_offset=69), [Constant('eeeee', lineno=1, col_offset=64, end_lineno=1, end_col_offset=69)], [], lineno=1, col_offset=64, end_lineno=1, end_col_offset=69), lineno=1, col_offset=64, end_lineno=1, end_col_offset=69)], None, lineno=1, col_offset=2, end_lineno=1, end_col_offset=77)]",
                check_eval="[Expr(Call(Name('__swrite__', Load(), lineno=1, col_offset=8, end_lineno=3, end_col_offset=0), [Expr(Call(Attribute(Name('str', Load(), lineno=1, col_offset=8, end_lineno=3, end_col_offset=3), 'split', Load(), lineno=1, col_offset=8, end_lineno=3, end_col_offset=9), [Constant('this should show a list of strings', None, lineno=2, col_offset=0, end_lineno=4, end_col_offset=36)], [], lineno=1, col_offset=8, end_lineno=4, end_col_offset=37), lineno=1, col_offset=8, end_lineno=4, end_col_offset=37)], [], lineno=1, col_offset=8, end_lineno=3, end_col_offset=0), lineno=1, col_offset=8, end_lineno=3, end_col_offset=0)]",
                check_for="[For(Name('i', Store(), lineno=1, col_offset=6, end_lineno=1, end_col_offset=21), Tuple([Constant(1, None, lineno=1, col_offset=11, end_lineno=1, end_col_offset=26), Constant(2, None, lineno=1, col_offset=13, end_lineno=1, end_col_offset=28), Constant(3, None, lineno=1, col_offset=15, end_lineno=1, end_col_offset=30)], Load(), lineno=1, col_offset=11, end_lineno=1, end_col_offset=30), [Expr(Call(Name('__write__', Load(), lineno=1, col_offset=18, end_lineno=1, end_col_offset=24), [Constant('abcdef', lineno=1, col_offset=18, end_lineno=1, end_col_offset=24)], [], lineno=1, col_offset=18, end_lineno=1, end_col_offset=24), lineno=1, col_offset=18, end_lineno=1, end_col_offset=24)], [], None, lineno=1, col_offset=2, end_lineno=1, end_col_offset=32)]",
                check_if="[If(Name('i', Load(), lineno=1, col_offset=5, end_lineno=1, end_col_offset=10), [Expr(Call(Name('__write__', Load(), lineno=1, col_offset=8, end_lineno=1, end_col_offset=11), [Constant('aaa', lineno=1, col_offset=8, end_lineno=1, end_col_offset=11)], [], lineno=1, col_offset=8, end_lineno=1, end_col_offset=11), lineno=1, col_offset=8, end_lineno=1, end_col_offset=11)], [If(Name('j', Load(), lineno=1, col_offset=18, end_lineno=1, end_col_offset=25), [Expr(Call(Name('__write__', Load(), lineno=1, col_offset=21, end_lineno=1, end_col_offset=24), [Constant('bbb', lineno=1, col_offset=21, end_lineno=1, end_col_offset=24)], [], lineno=1, col_offset=21, end_lineno=1, end_col_offset=24), lineno=1, col_offset=21, end_lineno=1, end_col_offset=24)], [If(Name('k', Load(), lineno=1, col_offset=31, end_lineno=1, end_col_offset=38), [Expr(Call(Name('__write__', Load(), lineno=1, col_offset=34, end_lineno=1, end_col_offset=37), [Constant('ccc', lineno=1, col_offset=34, end_lineno=1, end_col_offset=37)], [], lineno=1, col_offset=34, end_lineno=1, end_col_offset=37), lineno=1, col_offset=34, end_lineno=1, end_col_offset=37)], [Expr(Call(Name('__write__', Load(), lineno=1, col_offset=45, end_lineno=1, end_col_offset=48), [Constant('ddd', lineno=1, col_offset=45, end_lineno=1, end_col_offset=48)], [], lineno=1, col_offset=45, end_lineno=1, end_col_offset=48), lineno=1, col_offset=45, end_lineno=1, end_col_offset=48)], lineno=1, col_offset=26, end_lineno=1, end_col_offset=44)], lineno=1, col_offset=13, end_lineno=1, end_col_offset=31)], lineno=1, col_offset=2, end_lineno=1, end_col_offset=55)]",
                check_while="[While(Compare(Name('i', Load(), lineno=1, col_offset=8, end_lineno=1, end_col_offset=19), [Lt()], [Constant(10, None, lineno=1, col_offset=10, end_lineno=1, end_col_offset=22)], lineno=1, col_offset=8, end_lineno=1, end_col_offset=22), [Expr(Call(Name('__write__', Load(), lineno=1, col_offset=14, end_lineno=1, end_col_offset=20), [Constant('abcdef', lineno=1, col_offset=14, end_lineno=1, end_col_offset=20)], [], lineno=1, col_offset=14, end_lineno=1, end_col_offset=20), lineno=1, col_offset=14, end_lineno=1, end_col_offset=20)], [], lineno=1, col_offset=2, end_lineno=1, end_col_offset=30)]",
                check_try_0="[Expr(Call(Name('__write__', Load(), lineno=1, col_offset=0, end_lineno=1, end_col_offset=3), [Constant('aaa', lineno=1, col_offset=0, end_lineno=1, end_col_offset=3)], [], lineno=1, col_offset=0, end_lineno=1, end_col_offset=3), lineno=1, col_offset=0, end_lineno=1, end_col_offset=3), Try([Expr(Call(Name('__write__', Load(), lineno=1, col_offset=10, end_lineno=1, end_col_offset=13), [Constant('bbb', lineno=1, col_offset=10, end_lineno=1, end_col_offset=13)], [], lineno=1, col_offset=10, end_lineno=1, end_col_offset=13), lineno=1, col_offset=10, end_lineno=1, end_col_offset=13)], [ExceptHandler(None, None, [Expr(Call(Name('__write__', Load(), lineno=1, col_offset=23, end_lineno=1, end_col_offset=26), [Constant('ccc', lineno=1, col_offset=23, end_lineno=1, end_col_offset=26)], [], lineno=1, col_offset=23, end_lineno=1, end_col_offset=26), lineno=1, col_offset=23, end_lineno=1, end_col_offset=26)], lineno=1, col_offset=15, end_lineno=4, end_col_offset=5)], [], [], lineno=1, col_offset=5, end_lineno=1, end_col_offset=8)]",
                check_try_1="[Expr(Call(Name('__write__', Load(), lineno=1, col_offset=0, end_lineno=1, end_col_offset=3), [Constant('aaa', lineno=1, col_offset=0, end_lineno=1, end_col_offset=3)], [], lineno=1, col_offset=0, end_lineno=1, end_col_offset=3), lineno=1, col_offset=0, end_lineno=1, end_col_offset=3), Try([Expr(Call(Name('__write__', Load(), lineno=1, col_offset=10, end_lineno=1, end_col_offset=13), [Constant('bbb', lineno=1, col_offset=10, end_lineno=1, end_col_offset=13)], [], lineno=1, col_offset=10, end_lineno=1, end_col_offset=13), lineno=1, col_offset=10, end_lineno=1, end_col_offset=13)], [ExceptHandler(Name('ValueError', Load(), lineno=3, col_offset=7, end_lineno=3, end_col_offset=17), None, [Expr(Call(Name('__write__', Load(), lineno=1, col_offset=34, end_lineno=1, end_col_offset=37), [Constant('eee', lineno=1, col_offset=34, end_lineno=1, end_col_offset=37)], [], lineno=1, col_offset=34, end_lineno=1, end_col_offset=37), lineno=1, col_offset=34, end_lineno=1, end_col_offset=37)], lineno=1, col_offset=15, end_lineno=4, end_col_offset=5), ExceptHandler(None, None, [Expr(Call(Name('__write__', Load(), lineno=1, col_offset=47, end_lineno=1, end_col_offset=50), [Constant('ccc', lineno=1, col_offset=47, end_lineno=1, end_col_offset=50)], [], lineno=1, col_offset=47, end_lineno=1, end_col_offset=50), lineno=1, col_offset=47, end_lineno=1, end_col_offset=50)], lineno=1, col_offset=39, end_lineno=4, end_col_offset=5)], [], [], lineno=1, col_offset=5, end_lineno=1, end_col_offset=8)]",
                check_try_2="[Expr(Call(Name('__write__', Load(), lineno=1, col_offset=0, end_lineno=1, end_col_offset=3), [Constant('aaa', lineno=1, col_offset=0, end_lineno=1, end_col_offset=3)], [], lineno=1, col_offset=0, end_lineno=1, end_col_offset=3), lineno=1, col_offset=0, end_lineno=1, end_col_offset=3), Try([Expr(Call(Name('__write__', Load(), lineno=1, col_offset=10, end_lineno=1, end_col_offset=13), [Constant('bbb', lineno=1, col_offset=10, end_lineno=1, end_col_offset=13)], [], lineno=1, col_offset=10, end_lineno=1, end_col_offset=13), lineno=1, col_offset=10, end_lineno=1, end_col_offset=13)], [ExceptHandler(Name('ValueError', Load(), lineno=3, col_offset=7, end_lineno=3, end_col_offset=17), None, [Expr(Call(Name('__write__', Load(), lineno=1, col_offset=34, end_lineno=1, end_col_offset=37), [Constant('eee', lineno=1, col_offset=34, end_lineno=1, end_col_offset=37)], [], lineno=1, col_offset=34, end_lineno=1, end_col_offset=37), lineno=1, col_offset=34, end_lineno=1, end_col_offset=37)], lineno=1, col_offset=15, end_lineno=4, end_col_offset=5), ExceptHandler(None, None, [Expr(Call(Name('__write__', Load(), lineno=1, col_offset=47, end_lineno=1, end_col_offset=50), [Constant('ccc', lineno=1, col_offset=47, end_lineno=1, end_col_offset=50)], [], lineno=1, col_offset=47, end_lineno=1, end_col_offset=50), lineno=1, col_offset=47, end_lineno=1, end_col_offset=50)], lineno=1, col_offset=39, end_lineno=4, end_col_offset=5)], [Expr(Call(Name('__write__', Load(), lineno=1, col_offset=58, end_lineno=1, end_col_offset=61), [Constant('ddd', lineno=1, col_offset=58, end_lineno=1, end_col_offset=61)], [], lineno=1, col_offset=58, end_lineno=1, end_col_offset=61), lineno=1, col_offset=58, end_lineno=1, end_col_offset=61)], [], lineno=1, col_offset=5, end_lineno=1, end_col_offset=8)]",
                check_try_3="[Expr(Call(Name('__write__', Load(), lineno=1, col_offset=0, end_lineno=1, end_col_offset=3), [Constant('aaa', lineno=1, col_offset=0, end_lineno=1, end_col_offset=3)], [], lineno=1, col_offset=0, end_lineno=1, end_col_offset=3), lineno=1, col_offset=0, end_lineno=1, end_col_offset=3), Try([Expr(Call(Name('__write__', Load(), lineno=1, col_offset=10, end_lineno=1, end_col_offset=13), [Constant('bbb', lineno=1, col_offset=10, end_lineno=1, end_col_offset=13)], [], lineno=1, col_offset=10, end_lineno=1, end_col_offset=13), lineno=1, col_offset=10, end_lineno=1, end_col_offset=13)], [ExceptHandler(Name('ValueError', Load(), lineno=3, col_offset=7, end_lineno=3, end_col_offset=17), None, [Expr(Call(Name('__write__', Load(), lineno=1, col_offset=34, end_lineno=1, end_col_offset=37), [Constant('eee', lineno=1, col_offset=34, end_lineno=1, end_col_offset=37)], [], lineno=1, col_offset=34, end_lineno=1, end_col_offset=37), lineno=1, col_offset=34, end_lineno=1, end_col_offset=37)], lineno=1, col_offset=15, end_lineno=4, end_col_offset=5), ExceptHandler(None, None, [Expr(Call(Name('__write__', Load(), lineno=1, col_offset=47, end_lineno=1, end_col_offset=50), [Constant('ccc', lineno=1, col_offset=47, end_lineno=1, end_col_offset=50)], [], lineno=1, col_offset=47, end_lineno=1, end_col_offset=50), lineno=1, col_offset=47, end_lineno=1, end_col_offset=50)], lineno=1, col_offset=39, end_lineno=4, end_col_offset=5)], [Expr(Call(Name('__write__', Load(), lineno=1, col_offset=58, end_lineno=1, end_col_offset=61), [Constant('ddd', lineno=1, col_offset=58, end_lineno=1, end_col_offset=61)], [], lineno=1, col_offset=58, end_lineno=1, end_col_offset=61), lineno=1, col_offset=58, end_lineno=1, end_col_offset=61)], [Expr(Call(Name('__write__', Load(), lineno=1, col_offset=72, end_lineno=1, end_col_offset=75), [Constant('fff', lineno=1, col_offset=72, end_lineno=1, end_col_offset=75)], [], lineno=1, col_offset=72, end_lineno=1, end_col_offset=75), lineno=1, col_offset=72, end_lineno=1, end_col_offset=75)], lineno=1, col_offset=5, end_lineno=1, end_col_offset=8)]",
                check_script="[Assign([Name('a', Store(), lineno=1, col_offset=10, end_lineno=3, end_col_offset=1)], Constant(1, None, lineno=1, col_offset=12, end_lineno=3, end_col_offset=3), None, lineno=1, col_offset=10, end_lineno=3, end_col_offset=3), Assign([Name('b', Store(), lineno=2, col_offset=0, end_lineno=4, end_col_offset=1)], Constant(2, None, lineno=2, col_offset=2, end_lineno=4, end_col_offset=3), None, lineno=2, col_offset=0, end_lineno=4, end_col_offset=3), Assign([Name('c', Store(), lineno=3, col_offset=0, end_lineno=5, end_col_offset=1)], Constant(3, None, lineno=3, col_offset=2, end_lineno=5, end_col_offset=3), None, lineno=3, col_offset=0, end_lineno=5, end_col_offset=3)]",
                )
    else:
        if isPy3:
            _ct3 = "[Expr(Call(Name('__write__', Load(), lineno=1, col_offset=0), [Str('aaa', lineno=1, col_offset=0)], [],sNN lineno=1, col_offset=0), lineno=1, col_offset=0), Try([Expr(Call(Name('__write__', Load(), lineno=1, col_offset=10), [Str('bbb', lineno=1, col_offset=10)], [],sNN lineno=1, col_offset=10), lineno=1, col_offset=10)], [ExceptHandler(Name('ValueError', Load(), lineno=3, col_offset=7), None, [Expr(Call(Name('__write__', Load(), lineno=1, col_offset=34), [Str('eee', lineno=1, col_offset=34)], [],sNN lineno=1, col_offset=34), lineno=1, col_offset=34)], lineno=1, col_offset=15), ExceptHandler(None, None, [Expr(Call(Name('__write__', Load(), lineno=1, col_offset=47), [Str('ccc', lineno=1, col_offset=47)], [],sNN lineno=1, col_offset=47), lineno=1, col_offset=47)], lineno=1, col_offset=39)], [Expr(Call(Name('__write__', Load(), lineno=1, col_offset=58), [Str('ddd', lineno=1, col_offset=58)], [],sNN lineno=1, col_offset=58), lineno=1, col_offset=58)], [Expr(Call(Name('__write__', Load(), lineno=1, col_offset=72), [Str('fff', lineno=1, col_offset=72)], [],sNN lineno=1, col_offset=72), lineno=1, col_offset=72)], lineno=1, col_offset=5)]" % locals()
        else:
            _ct3 = "[Expr(Call(Name('__write__', Load(), lineno=1, col_offset=0), [Str('aaa', lineno=1, col_offset=0)], [],sNN lineno=1, col_offset=0), lineno=1, col_offset=0), TryFinally([TryExcept([Expr(Call(Name('__write__', Load(), lineno=1, col_offset=10), [Str('bbb', lineno=1, col_offset=10)], [],sNN lineno=1, col_offset=10), lineno=1, col_offset=10)], [ExceptHandler(Name('ValueError', Load(), lineno=3, col_offset=7), None, [Expr(Call(Name('__write__', Load(), lineno=1, col_offset=34), [Str('eee', lineno=1, col_offset=34)], [],sNN lineno=1, col_offset=34), lineno=1, col_offset=34)], lineno=1, col_offset=15), ExceptHandler(None, None, [Expr(Call(Name('__write__', Load(), lineno=1, col_offset=47), [Str('ccc', lineno=1, col_offset=47)], [],sNN lineno=1, col_offset=47), lineno=1, col_offset=47)], lineno=1, col_offset=39)], [Expr(Call(Name('__write__', Load(), lineno=1, col_offset=58), [Str('ddd', lineno=1, col_offset=58)], [],sNN lineno=1, col_offset=58), lineno=1, col_offset=58)], lineno=1, col_offset=5)], [Expr(Call(Name('__write__', Load(), lineno=1, col_offset=72), [Str('fff', lineno=1, col_offset=72)], [],sNN lineno=1, col_offset=72), lineno=1, col_offset=72)], lineno=1, col_offset=5)]"
        results=dict(
                check_break="[For(Name('i', Store(), lineno=1, col_offset=6), Tuple([Num(1, lineno=1, col_offset=11), Num(2, lineno=1, col_offset=13), Num(3, lineno=1, col_offset=15)], Load(), lineno=1, col_offset=11), [Expr(Call(Name('__write__', Load(), lineno=1, col_offset=18), [Str('abcdef', lineno=1, col_offset=18)], [],sNN lineno=1, col_offset=18), lineno=1, col_offset=18), If(Compare(Name('i', Load(), lineno=1, col_offset=29), [Eq()], [Num(3, lineno=1, col_offset=32)], lineno=1, col_offset=29), [Break( lineno=1, col_offset=37)], [], lineno=1, col_offset=26)], [Expr(Call(Name('__write__', Load(), lineno=1, col_offset=61), [Str('eeeee', lineno=1, col_offset=61)], [],sNN lineno=1, col_offset=61), lineno=1, col_offset=61)], lineno=1, col_offset=2)]",
                check_continue="[For(Name('i', Store(), lineno=1, col_offset=6), Tuple([Num(1, lineno=1, col_offset=11), Num(2, lineno=1, col_offset=13), Num(3, lineno=1, col_offset=15)], Load(), lineno=1, col_offset=11), [Expr(Call(Name('__write__', Load(), lineno=1, col_offset=18), [Str('abcdef', lineno=1, col_offset=18)], [],sNN lineno=1, col_offset=18), lineno=1, col_offset=18), If(Compare(Name('i', Load(), lineno=1, col_offset=29), [Eq()], [Num(3, lineno=1, col_offset=32)], lineno=1, col_offset=29), [Continue( lineno=1, col_offset=37)], [], lineno=1, col_offset=26)], [Expr(Call(Name('__write__', Load(), lineno=1, col_offset=64), [Str('eeeee', lineno=1, col_offset=64)], [],sNN lineno=1, col_offset=64), lineno=1, col_offset=64)], lineno=1, col_offset=2)]",
                check_eval="[Expr(Call(Name('__swrite__', Load(), lineno=1, col_offset=8), [Expr(Call(Attribute(Name('str', Load(), lineno=1, col_offset=8), 'split', Load(), lineno=1, col_offset=%(CO0)s), [Str('this should show a list of strings', lineno=2, col_offset=%(CO1)s)], [],sNN lineno=1, col_offset=%(CO2)s), lineno=1, col_offset=8)], [],sNN lineno=1, col_offset=8), lineno=1, col_offset=8)]",
                check_for="[For(Name('i', Store(), lineno=1, col_offset=6), Tuple([Num(1, lineno=1, col_offset=11), Num(2, lineno=1, col_offset=13), Num(3, lineno=1, col_offset=15)], Load(), lineno=1, col_offset=11), [Expr(Call(Name('__write__', Load(), lineno=1, col_offset=18), [Str('abcdef', lineno=1, col_offset=18)], [],sNN lineno=1, col_offset=18), lineno=1, col_offset=18)], [], lineno=1, col_offset=2)]",
                check_if="[If(Name('i', Load(), lineno=1, col_offset=5), [Expr(Call(Name('__write__', Load(), lineno=1, col_offset=8), [Str('aaa', lineno=1, col_offset=8)], [],sNN lineno=1, col_offset=8), lineno=1, col_offset=8)], [If(Name('j', Load(), lineno=1, col_offset=18), [Expr(Call(Name('__write__', Load(), lineno=1, col_offset=21), [Str('bbb', lineno=1, col_offset=21)], [],sNN lineno=1, col_offset=21), lineno=1, col_offset=21)], [If(Name('k', Load(), lineno=1, col_offset=31), [Expr(Call(Name('__write__', Load(), lineno=1, col_offset=34), [Str('ccc', lineno=1, col_offset=34)], [],sNN lineno=1, col_offset=34), lineno=1, col_offset=34)], [Expr(Call(Name('__write__', Load(), lineno=1, col_offset=45), [Str('ddd', lineno=1, col_offset=45)], [],sNN lineno=1, col_offset=45), lineno=1, col_offset=45)], lineno=1, col_offset=26)], lineno=1, col_offset=13)], lineno=1, col_offset=2)]",
                check_while="[While(Compare(Name('i', Load(), lineno=1, col_offset=8), [Lt()], [Num(10, lineno=1, col_offset=10)], lineno=1, col_offset=8), [Expr(Call(Name('__write__', Load(), lineno=1, col_offset=14), [Str('abcdef', lineno=1, col_offset=14)], [],sNN lineno=1, col_offset=14), lineno=1, col_offset=14)], [], lineno=1, col_offset=2)]",
                check_try_0="[Expr(Call(Name('__write__', Load(), lineno=1, col_offset=0), [Str('aaa', lineno=1, col_offset=0)], [],sNN lineno=1, col_offset=0), lineno=1, col_offset=0), sTE([Expr(Call(Name('__write__', Load(), lineno=1, col_offset=10), [Str('bbb', lineno=1, col_offset=10)], [],sNN lineno=1, col_offset=10), lineno=1, col_offset=10)], [ExceptHandler(None, None, [Expr(Call(Name('__write__', Load(), lineno=1, col_offset=23), [Str('ccc', lineno=1, col_offset=23)], [],sNN lineno=1, col_offset=23), lineno=1, col_offset=23)], lineno=1, col_offset=15)], [],sTFL lineno=1, col_offset=5)]",
                check_try_1="[Expr(Call(Name('__write__', Load(), lineno=1, col_offset=0), [Str('aaa', lineno=1, col_offset=0)], [],sNN lineno=1, col_offset=0), lineno=1, col_offset=0), sTE([Expr(Call(Name('__write__', Load(), lineno=1, col_offset=10), [Str('bbb', lineno=1, col_offset=10)], [],sNN lineno=1, col_offset=10), lineno=1, col_offset=10)], [ExceptHandler(Name('ValueError', Load(), lineno=3, col_offset=7), None, [Expr(Call(Name('__write__', Load(), lineno=1, col_offset=34), [Str('eee', lineno=1, col_offset=34)], [],sNN lineno=1, col_offset=34), lineno=1, col_offset=34)], lineno=1, col_offset=15), ExceptHandler(None, None, [Expr(Call(Name('__write__', Load(), lineno=1, col_offset=47), [Str('ccc', lineno=1, col_offset=47)], [],sNN lineno=1, col_offset=47), lineno=1, col_offset=47)], lineno=1, col_offset=39)], [],sTFL lineno=1, col_offset=5)]",
                check_try_2="[Expr(Call(Name('__write__', Load(), lineno=1, col_offset=0), [Str('aaa', lineno=1, col_offset=0)], [],sNN lineno=1, col_offset=0), lineno=1, col_offset=0), sTE([Expr(Call(Name('__write__', Load(), lineno=1, col_offset=10), [Str('bbb', lineno=1, col_offset=10)], [],sNN lineno=1, col_offset=10), lineno=1, col_offset=10)], [ExceptHandler(Name('ValueError', Load(), lineno=3, col_offset=7), None, [Expr(Call(Name('__write__', Load(), lineno=1, col_offset=34), [Str('eee', lineno=1, col_offset=34)], [],sNN lineno=1, col_offset=34), lineno=1, col_offset=34)], lineno=1, col_offset=15), ExceptHandler(None, None, [Expr(Call(Name('__write__', Load(), lineno=1, col_offset=47), [Str('ccc', lineno=1, col_offset=47)], [],sNN lineno=1, col_offset=47), lineno=1, col_offset=47)], lineno=1, col_offset=39)], [Expr(Call(Name('__write__', Load(), lineno=1, col_offset=58), [Str('ddd', lineno=1, col_offset=58)], [],sNN lineno=1, col_offset=58), lineno=1, col_offset=58)],sTFL lineno=1, col_offset=5)]",
                check_try_3=_ct3,
                check_script="[Assign([Name('a', Store(), lineno=1, col_offset=10)], Num(1, lineno=1, col_offset=12), lineno=1, col_offset=10), Assign([Name('b', Store(), lineno=2, col_offset=0)], Num(2, lineno=2, col_offset=2), lineno=2, col_offset=0), Assign([Name('c', Store(), lineno=3, col_offset=0)], Num(3, lineno=3, col_offset=2), lineno=3, col_offset=0)]",
                )
        del _ct3

    def check_for(self):
        self.assertEqualStr(P__preppy('{{for i in 1,2,3}}abcdef{{endfor}}'), self.results['check_for'])

    def check_break(self):
        self.assertEqualStr(P__preppy('{{for i in 1,2,3}}abcdef{{if i==3}}{{break}}{{endif}}{{else}}eeeee{{endfor}}'), self.results['check_break'])

    def check_break_outside_loop_fails(self):
        self.assertRaises(SyntaxError,P__preppy,'{{if i==3}}{{break}}{{endif}}')

    def check_continue(self):
        self.assertEqualStr(P__preppy('{{for i in 1,2,3}}abcdef{{if i==3}}{{continue}}{{endif}}{{else}}eeeee{{endfor}}'), self.results['check_continue'])

    def check_continue_outside_loop_fails(self):
        self.assertRaises(SyntaxError,P__preppy,'{{if i==3}}{{continue}}{{endif}}')

    def check_while(self):
        self.assertEqualStr(P__preppy('{{while i<10}}abcdef{{endwhile}}'), self.results['check_while'])

    def check_eval(self):
        #3.4 seems to improve on the col_offsets
        if isPy34 and sys.version_info[2]<3:
            CO0 = 12
            CO1 = 0
            CO2 = 17
            if isPy35:
                NN = ''
                CO2 = 8
                CO0 = 8
        else:
            CO0 = 8
            CO1 = 0
            CO2 = 8
        self.assertEqualStr(P__preppy('{{eval}}str.split(\n"this should show a list of strings")\n{{endeval}}'), self.results['check_eval'] % vars())

    def check_script(self):
        self.assertEqualStr(P__preppy('{{script}}a=1\nb=2\nc=3{{endscript}}'), self.results['check_script'])

    def check_if(self):
        self.assertEqualStr(P__preppy('{{if i}}aaa{{elif j}}bbb{{elif k}}ccc{{else}}ddd{{endif}}'), self.results['check_if'])

    def check_try_0(self):
        if isPy35:
            NN = ''
        self.assertEqualStr(P__preppy('aaa{{try}}bbb{{except}}ccc{{endtry}}'), self.results['check_try_0']%locals())

    def check_try_1(self):
        if isPy35:
            NN = ''
        self.assertEqualStr(P__preppy('aaa{{try}}bbb{{except ValueError}}eee{{except}}ccc{{endtry}}'), self.results['check_try_1']%locals())

    def check_try_2(self):
        self.assertEqualStr(P__preppy('aaa{{try}}bbb{{except ValueError}}eee{{except}}ccc{{else}}ddd{{endtry}}'), self.results['check_try_2'] % locals())

    def check_try_3(self):
        self.assertEqualStr(P__preppy('aaa{{try}}bbb{{except ValueError}}eee{{except}}ccc{{else}}ddd{{finally}}fff{{endtry}}'),self.results['check_try_3'])

    def check_try_4(self):
        self.assertRaises(SyntaxError,P__preppy,'{{try}}bbb{{endtry}}')

    def check_try_5(self):
        self.assertRaises(SyntaxError,P__preppy,'{{try}}bbb{{else}}ddd{{endtry}}')

def makeSuite():
    return unittest.TestSuite((unittest.makeSuite(PreppyParserTestCase,'check'),))

if __name__=='__main__':
    runner = unittest.TextTestRunner()
    runner.run(makeSuite())
