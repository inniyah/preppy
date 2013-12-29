#copyright ReportLab Inc. 2000-2012
#see license.txt for license details

"""preppy - a Python preprocessor.

This is the Python equivalent of ASP or JSP - a preprocessor which lets you
embed python expressions, loops and conditionals, and 'scriptlets' in any
kind of text file.  It provides a very natural solution for generating
dynamic HTML pages, which is not connected to any particular web server
architecture.

You create a template file (conventionally ending in .prep) containing
python expressions, loops and conditionals, and scripts.  These occur
between double curly braces:
   Dear {{surname}},
   You owe us {{amount}} {{if amount>1000}}which is pretty serious{{endif}}

On first use or any any change in the template, this is normally converted to a
python source module 'in memory', then to a compiled pyc file which is saved to
disk alongside the original.  Options control this; you can operate entirely
in memory, or look at the generated python code if you wish.

On subsequent use, the generated module is imported and loaded directly.
The module contains a run(...) function; you can pass in a dictionary of
parameters (such as the surname and amount parameters above), and optionally
an output stream or output-collection function if you don't want it to go to
standard output.

The command line options let you run modules with hand-input parameters -
useful for basic testing - and also to batch-compile or clean directories.
As with python scripts, it is a good idea to compile prep files on installation,
since unix applications may run as a different user and not have the needed
permission to store compiled modules.

"""
VERSION = '2.0'
__version__ = VERSION

USAGE = """
The command line interface lets you test, compile and clean up:

    preppy modulename [arg1=value1, arg2=value2.....]
       - shorthand for 'preppy run ...', see below.

    preppy run modulename [arg1=value1, arg2=value2.....]
       - runs the module, optionally with arguments.  e.g.
         preppy.py flintstone.prep name=fred sex=m

    preppy.py compile [-f] [-v] [-p] module1[.prep] module2[.prep] module3 ...
       - compiles explicit modules

    preppy.py compile [-f] [-v] [-p] dirname1  dirname2 ...
       - compiles all prep files in directory recursively

    preppy.py clean dirname1 dirname2 ...19
       - removes any py or pyc files created from past compilations


"""

STARTDELIMITER = "{{"
ENDDELIMITER = "}}"
QSTARTDELIMITER = "{${"
QENDDELIMITER = "}$}"
QUOTE = "$"
QUOTEQUOTE = "$$"
# SEQUENCE OF REPLACEMENTS FOR UNESCAPING A STRING.
UNESCAPES = ((QSTARTDELIMITER, STARTDELIMITER), (QENDDELIMITER, ENDDELIMITER), (QUOTEQUOTE, QUOTE))

import re, sys, os, imp, struct, tokenize, token, ast, traceback, time, marshal, py_compile, pickle
from hashlib import md5
isPy3 = sys.version_info.major == 3
from xml.sax.saxutils import escape as xmlEscape
from collections import namedtuple
Token = namedtuple('Token','kind lineno start end')

if isPy3:
    from io import BytesIO, StringIO
    def __preppy__vlhs__(s,NAME=token.NAME,ENDMARKER=token.ENDMARKER):
        try:
            L = list(tokenize.tokenize(BytesIO(s.strip().encode('utf8')).readline))
        except:
            return False
        return len(L)<=3 and L[-2][0]==NAME and L[-1][0]==ENDMARKER

    class SafeString(bytes):
        pass
    class SafeUnicode(str):
        pass
    _ucvn = '__str__'   #unicode conversion
    _bcvn = '__bytes__' #bytes conversion
    _ncvt = str         #native converter
    bytesT = bytes
    unicodeT = str
    strTypes = (str,bytes)
    import builtins
    rl_exec = getattr(builtins,'exec')
    del builtins
else:
    from StringIO import StringIO
    BytesIO = StringIO
    def __preppy__vlhs__(s,NAME=token.NAME,ENDMARKER=token.ENDMARKER):
        L = []
        try:
            tokenize.tokenize(BytesIO(s.strip()).readline,lambda *a: L.append(a))
        except:
            return False
        return len(L)==2 and L[0][0]==NAME and L[1][0]==ENDMARKER

    class SafeString(str):
        pass
    class SafeUnicode(unicode):
        pass
    _ucvn = '__unicode__'
    _bcvn = '__str__'
    _ncvt = unicode
    bytesT = str
    unicodeT = unicode
    strTypes = basestring
    def rl_exec(obj, G=None, L=None):
        if G is None:
            frame = sys._getframe(1)
            G = frame.f_globals
            if L is None:
                L = frame.f_locals
            del frame
        elif L is None:
            L = G
        exec("""exec obj in G, L""")

def asUtf8(s):
    return s if isinstance(s,bytesT) else s.encode('utf8')
def getMd5(s):
    return md5(asUtf8(s)+asUtf8(VERSION)).hexdigest()

#Andy's standard quote for django
_safeBase = SafeString, SafeUnicode
def stdQuote(s):
    if not isinstance(s,strTypes):
        if s is None: return '' #we usually don't want output
        cnv = getattr(s,_ucvn,None)
        if not cnv:
            cnv = getattr(s,_bcvn,None)
        s = cnv() if cnv else str(s)
    if isinstance(s,_safeBase):
        if isinstance(s,SafeString):
            s = s.decode('utf8')
        return s
    elif not isinstance(s,_ncvt):
        s = s.decode('utf8')
    return xmlEscape(s)

def pnl(s):
    '''print without a lineend'''
    if isinstance(s,unicodeT):
        s = s.encode(sys.stdout.encoding,'replace')
    sys.stdout.write(s)

def pel(s):
    '''print with a line ending'''
    pnl(s)
    pnl('\n')

def unescape(s, unescapes=UNESCAPES):
    for (old, new) in unescapes:
        s = s.replace(old, new)
    return s


teststring = """
this test script should produce a runnable program
{{script}}
  class X:
      pass
  x = X()
  x.a = "THE A VALUE OF X"
  yislonger = "y is longer!"
  import math
  a = dictionary = {"key": "value", "key2": "value2", "10%": "TEN PERCENT"}
  loop = "LOOP"
{{endscript}}
this line has a percent in it 10%
here is the a value in x: {{x.a}}
just a norml value here: {{yislonger}} string {{a["10%"]}}
 the sine of 12.3 is {{math.sin(12.3)}}
 {{script}} a=0 {{endscript}}
 these parens should be empty
 ({{if a:}}
conditional text{{endif}})
 {{script}} a=1
 {{endscript}}
 these parens should be full
 ({{if a:}}
conditional text{{endif}})
stuff between endif and while

{{while a==1:}} infinite {{loop}} forever!
{{script}} a=0 {{endscript}}
{{for (a,b) in dictionary.items():}}
the key in the dictionary is {{a}} and the value is {{b}}.  And below is a script
{{script}}
        # THIS IS A SCRIPT
        x = 2
        y = 3
        # END OF THE SCRIPT
{{endscript}}
stuff after the script
{{endfor}}
stuff after the for stmt
{{endwhile}}
stuff after the while stmt

{{script}}
# test the free variables syntax error problem is gone
alpha = 3
def myfunction1(alpha=alpha):
    try:
        return free_variable # this would cause an error in an older version of preppy with python 2.2
    except:
        pass
    try:
        return alpha
    except:
        return "oops"
beta = myfunction1()
{{endscript}}
alpha = {{alpha}} and beta = {{beta}}

{${this is invalid but it's escaped, so no problem!}$}

end of text

{{script}}
# just a comment
{{endscript}}
stop here
"""

"""
# test code for quotestring
(qs, ds, c) = PreProcessor().quoteString(teststring, cursor=0)
print "---------quoted to ", c, `teststring[c:c+20]`
print qs
print "---------dict string"
print ds
"""
def dedent(text):
    """get rid of redundant indentation in text this dedenter IS NOT smart about converting tabs to spaces!!!"""
    lines = text.split("\n")
    # omit empty lines
    lempty = 0
    while lines:
        line0 = lines[0].strip()
        if line0 and line0[0]!='#': break
        del lines[0]
        lempty += 1
    if not lines: return "" # completely white
    line0 = lines[0]
    findfirstword = line0.find(line0.strip().split()[0])
    if findfirstword<0: raise ValueError('internal dedenting error')
    indent = line0[:findfirstword]
    linesout = []
    for l in lines:
        lines0 = l.strip()
        if not lines0 or lines0[0]=='#':
            linesout.append("")
            continue
        lindent = l[:findfirstword]
        if lindent!=indent:
            raise ValueError("inconsistent indent expected %s got %s in %s" % (repr(indent), repr(lindent), l))
        linesout.append(l[findfirstword:])
    return len(indent),'\n'.join(lempty*['']+linesout)


_pat = re.compile('{{\\s*|}}',re.M)
_s = re.compile(r'^(?P<start>while|if|elif|for|continue|break|try|except)(?P<startend>\s+|$)|(?P<def>def\s*)(?P<defend>\(|$)|(?P<end>else|script|eval|endwhile|endif|endscript|endeval|endfor|finally|endtry)(?:\s*$|(?P<endend>.+$))',re.DOTALL|re.M)

def _denumber(node,lineno=-1):
    if node.lineno!=lineno: node.lineno = lineno
    for child in node.getChildNodes(): _denumber(child,lineno)

class PreppyParser:
    def __init__(self,source,filename='[unknown]',sourcechecksum=None):
        self.__mangle = '_%s__'%self.__class__.__name__
        self._defSeen = 0
        self.source = source
        self.filename = filename
        self.sourcechecksum = sourcechecksum
        self.__inFor = self.__inWhile = 0

    def compile(self, display=0):
        self.code = compile(self.__get_ast(),self.filename,'exec')

    def getPycHeader(self):
        try:
            if getattr(self,'nosourcefile',0): raise ValueError('no source file')
            mtime = os.path.getmtime(self.filename)
        except:
            import time
            mtime = time.time()
        mtime = struct.pack('<i', mtime)
        return self.MAGIC + mtime

    def __lexerror(self, msg, pos):
        text = self.source
        pos0 = text.rfind('\n',0,pos)+1
        pos1 = text.find('\n',pos)
        if pos1<0: pos1 = len(text)
        raise SyntaxError('%s\n%s\n%s (near line %d of %s)' %(text[pos0:pos1],(' '*(pos-pos0)),msg,text.count('\n',0,pos)+1,self.filename))

    def __tokenize(self):
        text = self.source
        self._tokens = tokens = []
        a = tokens.append
        state = 0
        ix = 0
        for i in _pat.finditer(text):
            i0 = i.start()
            i1 = i.end()
            lineno = text.count('\n',0,ix)+1
            if i.group()!='}}':
                if state:
                    self.__lexerror('Unexpected {{', i0)
                else:
                    state = 1
                    if i0!=ix: a(Token('const',lineno,ix,i0))
                    ix = i1
            elif state:
                    state = 0
                    #here's where a preppy token is finalized
                    m = _s.match(text[ix:i0])
                    if m:
                        t = m.group('start')
                        if t:
                            if not m.group('startend'):
                                if t not in ('continue','break','try','except'):
                                    self.__lexerror('Bad %s' % t, i0)
                        else:
                            t = m.group('end')
                            if t:
                                ee = m.group('endend')
                                if ee and t!='else' and ee.strip()!=':': self.__lexerror('Bad %s' % t, i0)
                            else:
                                t = m.group('def')
                                if t:
                                    if not m.group('defend'): self.__lexerror('Bad %s' % t, i0)
                                    if self._defSeen:
                                        if self._defSeen>0:
                                            self.__lexerror('Only one def may be used',i0)
                                        else:
                                            self.__lexerror('def must come first',i0)
                                    else:
                                        self._defSeen = 1
                    else:
                        t = 'expr'  #expression
                    if not self._defSeen: self._defSeen = -1
                    if i0!=ix: a(Token(t,lineno,ix,i0))
                    ix = i1
        else:
            lineno = 0
        if state: self.__lexerror('Unterminated preppy token', ix)
        textLen = len(text)
        if ix!=textLen:
            lineno = text.count('\n',0,ix)+1
            a(Token('const',lineno,ix,textLen))
        a(Token('eof',lineno+1,textLen,textLen))
        self._tokenX = 0
        return tokens

    def __tokenText(self, colonRemove=False, strip=True, forceColonPass=False):
        t = self._tokens[self._tokenX]
        text = self.source[t.start:t.end]
        if strip: text = text.strip()
        if colonRemove or forceColonPass:
            if text.endswith(':'): text = text[:-1]
            if forceColonPass: text += ':\tpass\n'
        return unescape(text)

    def __tokenPop(self):
        t = self._tokens[self._tokenX]
        self._tokenX += 1
        return t

    def __colOffset(self,t):
        '''obtain the column offset corresponding to a specific token'''
        return t.start-max(self.source.rfind('\n',0,t.start),0)

    def __rparse(self,text):
        '''parse a raw fragment of code'''
        tf = ast.parse(text,filename=self.filename,mode='exec').body
        return tf

    def __iparse(self,text):
        '''parse a start fragment of code'''
        return self.__rparse(text)[0]

    def __preppy(self,funcs=['const','expr','while','if','for','script', 'eval','def', 'continue', 'break', 'try'],followers=['eof'],pop=True):
        C = []
        a = C.append
        mangle = self.__mangle
        tokens = self._tokens
        while 1:
            t = tokens[self._tokenX].kind
            if t in followers: break
            p = t in funcs and getattr(self,mangle+t) or self.__serror
            r = p()
            if isinstance(r,list): C += r
            elif r is not None: a(r)
        if pop:
            self.__tokenPop()
        return C

    def __def(self,followers=['endwhile']):
        try:
            n = self.__iparse('def get'+(self.__tokenText(forceColonPass=1).strip()[3:]))
        except:
            self.__error()
        t = self.__tokenPop()
        self._fnc_defn = t,n
        return None

    def __break(self,stmt='break'):
        text = self.__tokenText()
        if text!=stmt:
            self.__serror(msg='invalid %s statement' % stmt)
        elif not self.__inWhile and not self.__inFor:
            self.__serror(msg='%s statement outside while or for loop' % stmt)
        t = self.__tokenPop()
        n = getattr(ast,stmt.capitalize())(lineno=1,col_offset=0)
        self.__renumber(n,t)
        return n

    def __continue(self):
        return self.__break(stmt='continue')

    def __renumber(self,node,t,dcoffs=0):
        if isinstance(node,list):
            for f in node:
                self.__renumber(f,t,dcoffs=dcoffs)
            return
        if isinstance(t,Token):
            lineno_offset = t.lineno-1
            col_offset = self.__colOffset(t)
        else:
            lineno_offset, col_offset = t
        if 'col_offset' in node._attributes:
            if getattr(node,'lineno',1)==1:
                node.col_offset = getattr(node,'col_offset',0)+col_offset+dcoffs
            elif not hasattr(node,'col_offset'):
                node.col_offset = dcoffs
            else:
                node.col_offset += dcoffs
        if 'lineno' in node._attributes:
            node.lineno = getattr(node,'lineno',1)+lineno_offset
        t = lineno_offset,col_offset
        for f in ast.iter_child_nodes(node):
            self.__renumber(f,t,dcoffs=dcoffs)

    def __while(self,followers=['endwhile','else']):
        self.__inWhile += 1
        try:
            n = self.__iparse(self.__tokenText(forceColonPass=1))
        except:
            self.__error()
        t = self.__tokenPop()
        self.__renumber(n,t)
        n.body = self.__preppy(followers=followers)
        if self._tokens[self._tokenX-1].kind=='else':
            n.orelse = self.__preppy(followers='endfor')
        self.__inWhile -= 1
        return n

    def __for(self,followers=['endfor','else']):
        self.__inFor += 1
        try:
            n = self.__iparse(self.__tokenText(forceColonPass=1))
        except:
            self.__error()
        t = self.__tokenPop()
        self.__renumber(n,t)
        n.body = self.__preppy(followers=followers)
        if self._tokens[self._tokenX-1].kind=='else':
            n.orelse = self.__preppy(followers='endfor')
        self.__inFor -= 1
        return n

    def __try(self):
        text = self.__tokenText(colonRemove=1)
        if text!='try':
            self.__serror(msg='invalid try statement')
        t = self.__tokenPop()
        n = ast.Try(lineno=1,col_offset=0,handlers=[])
        self.__renumber(n,t)
        n.body = self.__preppy(followers=['except','finally'],pop=False)
        while 1:
            text = self.__tokenText(colonRemove=1)
            t = self.__tokenPop()
            if text.startswith('endtry'):
                if text != 'endtry':
                    self.__error('invalid endtry statement')
                return n
            elif text.startswith('finally'):
                if text != 'finally':
                    self.__error('invalid finally statement')
                n.finalbody = self.__preppy(followers=['endtry'])
                return n
            elif text.startswith('else'):
                if text != 'else':
                    self.__error('invalid else statement')
                n.orelse = self.__preppy(followers=['finally','endtry'],pop=False)
            elif text.startswith('except'):
                exh = self.__iparse('try:\n\tpass\n%s:\n\tpass\n' % text).handlers[0]
                exh.lineno = 1
                exh.col_offset = 0
                self.__renumber(exh,t)
                F = ['finally','else','endtry'] if text=='except' else ['except','finally','endtry','else']
                exh.body = self.__preppy(followers=F,pop=False)
                n.handlers.append(exh)
            else:
                self.__serr('invalid syntax in try statement')

    def __script(self,mode='script'):
        self.__tokenPop()
        dcoffs, text = dedent(self.__tokenText(strip=0,colonRemove=False))
        scriptMode = 'script'==mode
        if text:
            try:
                n = self.__rparse(text)
            except:
                self.__error()
        t = self.__tokenPop()
        end = 'end'+mode
        try:
            assert self._tokens[self._tokenX].kind==end
            self.__tokenPop()
        except:
            self.__error(end+' expected')
        if not text: return []
        if mode=='eval': n = ast.Expr(value=ast.Call(func=ast.Name(id='__swrite__',ctx=ast.Load()),args=n,keywords=[],starargs=None,kwargs=None))
        self.__renumber(n,t,dcoffs=dcoffs)
        return n

    def __eval(self):
        return self.__script(mode='eval')

    def __if(self,followers=['endif','elif','else']):
        tokens = self._tokens
        t = 'elif'
        I = None
        while t=='elif':
            try:
                text = self.__tokenText(forceColonPass=1)
                if text.startswith('elif'): text = 'if  '+text[4:]
                n = self.__iparse(text)
            except:
                self.__error()
            t = self.__tokenPop()
            n.body = self.__preppy(followers=followers)
            self.__renumber(n,t)
            if I:
                p.orelse = [n]
            else:
                I = n
            p = n
            t = tokens[self._tokenX-1].kind #we consumed the terminal in __preppy
            if t=='elif': self._tokenX -= 1
        if t=='else':
            p.orelse = self.__preppy(followers=['endif'])
        return I

    def __const(self):
        try:
            n = ast.Expr(value=ast.Call(func=ast.Name(id='__write__',ctx=ast.Load()),args=[ast.Str(s=self.__tokenText(strip=0))],keywords=[],starargs=None,kwargs=None))
        except:
            self.__error('bad constant')
        t = self.__tokenPop()
        self.__renumber(n,t)
        return n

    def __expr(self):
        t = self.__tokenText()
        try:
            n = ast.Expr(value=ast.Call(func=ast.Name(id='__swrite__',ctx=ast.Load()),args=[self.__rparse(t)[0].value],keywords=[],starargs=None,kwargs=None))
        except:
            self.__error('bad expression')
        t = self.__tokenPop()
        self.__renumber(n,t)
        return n

    def __error(self,msg='invalid syntax'):
        pos = self._tokens[self._tokenX].start
        f = StringIO()
        traceback.print_exc(file=f)
        f = f.getvalue()
        m = 'File "<string>", line '
        i = f.rfind('File "<string>", line ')
        if i<0:
            t, v = map(str,sys.exc_info()[:2])
            self.__lexerror('%s %s(%s)' % (msg, t, v),pos)
        else:
            i += len(m)
            f = f[i:].split('\n')
            n = int(f[0].strip())+self.source[:pos].count('\n')
            raise SyntaxError('  File %s, line %d\n%s' % (self.filename,n,'\n'.join(f[1:])))

    def __serror(self,msg='invalid syntax'):
        self.__lexerror(msg,self._tokens[self._tokenX].start)

    def __parse(self,text=None):
        if text: self.source = text
        self.__tokenize()
        return self.__preppy()

    @staticmethod
    def dump(node,include_attributes=True):
        return ('[%s]' % ', '.join(PreppyParser.dump(x,include_attributes=include_attributes) for x in node)
                if isinstance(node,list)
                else ast.dump(node,annotate_fields=False,include_attributes=include_attributes))

    def __get_ast(self):
        preppyNodes = self.__parse()
        if self._defSeen==1:
            t, F = self._fnc_defn
            argNames = [a.arg for a in F.args.args] if isPy3 else [a.id for a in F.args.args]
            if F.args.kwarg:
                kwargName = F.args.kwarg
                CKWA = []
            else:
                F.args.kwarg = kwargName = '__kwds__'
                CKWA = ["if %s: raise TypeError('get: unexpected keyword arguments %%r' %% %s)" % (kwargName,kwargName)]

            leadNodes=self.__rparse('\n'.join([
                "__lquoteFunc__=%s.setdefault('__lquoteFunc__',str)" % kwargName,
                "%s.pop('__lquoteFunc__')" % kwargName,
                "__quoteFunc__=%s.setdefault('__quoteFunc__',str)" % kwargName,
                "%s.pop('__quoteFunc__')" % kwargName,
                ] + CKWA + [
                "__append__=[].append",
                "__write__=lambda x:__append__(__lquoteFunc__(x))",
                "__swrite__=lambda x:__append__(__quoteFunc__(x))",
                ]))
            trailNodes = self.__rparse("return ''.join(__append__.__self__)")

            self.__renumber(F,t)
            self.__renumber(leadNodes,(0,0))
            self.__renumber(trailNodes,self._tokens[-1])
            preppyNodes = leadNodes + preppyNodes + trailNodes
            global _newPreambleAst
            if not _newPreambleAst:
                _newPreambleAst = self.__rparse(_newPreamble)
                self.__renumber(_newPreambleAst,self._tokens[-1])
            F.body = preppyNodes
            extraAst = [F]+_newPreambleAst
        else:
            global _preambleAst, _preamble
            if not _preambleAst:
                #_preamble = 'from unparse import Unparser\n'+_preamble.replace('NS = {}\n','NS = {};Unparser(M,__save_sys_stdout__)\n')
                _preambleAst = self.__rparse(_preamble)
                self.__renumber(_preambleAst,self._tokens[-1])
            M = ast.parse("def __code__(dictionary, outputfile, __write__,__swrite__,__save_sys_stdout__): pass",self.filename,mode='exec')
            self.__renumber(M,(-1,0))
            M.body[0].body = preppyNodes
            extraAst = self.__rparse('__preppy_nodes__=%r\n__preppy_filename__=%r\n' % (pickle.dumps(M),self.filename))+_preambleAst
        M = ast.parse('__checksum__=%r' % self.sourcechecksum,self.filename,mode='exec')
        M.body += extraAst
        return M

_preambleAst=None
_preamble='''import ast, pickle
from preppy import rl_exec
def run(dictionary, __write__=None, quoteFunc=str, outputfile=None):
    ### begin standard prologue
    import sys
    __save_sys_stdout__ = sys.stdout
    try: # compiled logic below
        try:
            # if outputfile is defined, blindly assume it supports file protocol, reset sys.stdout
            if outputfile is None:
                raise NameError
            stdout = sys.stdout = outputfile
        except NameError:
            stdout = sys.stdout
            outputfile = None
        # make sure quoteFunc is defined:
        if quoteFunc is None:
            raise ValueError("quoteFunc must be defined")
        globals()['__quoteFunc__'] = quoteFunc
        # make sure __write__ is defined
        try:
            if __write__ is None:
                raise NameError
            if outputfile and __write__:
                raise ValueError("do not define both outputfile (%s) and __write__ (%s)." %(outputfile, __write__))
            class stdout: pass
            stdout = sys.stdout = stdout()
            stdout.write = lambda x:__write__(quoteFunc(x))
        except NameError:
            __write__ = lambda x: stdout.write(quoteFunc(x))
        __swrite__ = lambda x: __write__(quoteFunc(x))
        M = pickle.loads(__preppy_nodes__)
        b = M.body[0].body
        for k in dictionary:
            try:
                if __preppy__vlhs__(k):
                    b.insert(0,ast.parse('%s=dictionary[%r]' % (k,k),'???',mode='exec').body[0])
            except:
                pass
        NS = {}
        rl_exec(compile(M,__preppy_filename__,'exec'),NS)
        NS['__code__'](dictionary,outputfile,__write__,__swrite__,__save_sys_stdout__)
    finally: #### end of compiled logic, standard cleanup
        import sys # for safety
        #print "resetting stdout", sys.stdout, "to", __save_sys_stdout__
        sys.stdout = __save_sys_stdout__
def getOutput(dictionary, quoteFunc=str):
    buf=[]
    run(dictionary,__write__=buf.append, quoteFunc=quoteFunc)
    return ''.join(buf)

def getOutputFromKeywords(quoteFunc=str, **kwds):
    buf=[]
    run(kwds,__write__=buf.append, quoteFunc=quoteFunc)
    return ''.join(buf)

if __name__=='__main__':
    run()
'''
_newPreambleAst=None
_newPreamble='''def run(*args,**kwds):
    raise ValueError('Wrong kind of prep file')
def getOutput(*args,**kwds):
    run()
if __name__=='__main__':
    run()
'''



def testgetOutput(name="testoutput"):
    mod = getModule(name,'.',savePyc=1,sourcetext=teststring,importModule=1)
    pel(mod.getOutput({}))

def testgetmodule(name="testoutput"):
    #name = "testpreppy"
    pel("trying to load", name)
    result = getPreppyModule(name, verbose=1)
    pel( "load successful! running result")
    pel("=" * 100)
    result.run({})
def rl_get_module(name,dir):
    f, p, desc= imp.find_module(name,[dir])
    if sys.modules.has_key(name):
        om = sys.modules[name]
        del sys.modules[name]
    else:
        om = None
    try:
        try:
            return imp.load_module(name,f,p,desc)
        except:
            raise ImportError('%s[%s]' % (name,dir))
    finally:
        if om: sys.modules[name] = om
        del om
        if f: f.close()

# cache found modules by source file name
FILE_MODULES = {}
SOURCE_MODULES = {}
def getModule(name,
              directory=".",
              source_extension=".prep",
              verbose=0,
              savefile=None,
              sourcetext=None,
              savePy=0,
              force=0,
              savePyc=1,
              importModule=1,_globals=None):
    """Returns a python module implementing the template, compiling if needed.

    force: ignore up-to-date checks and always recompile.
    """
    if isinstance(name,bytesT): name = name.decode('utf8')
    if isinstance(directory,bytesT): directory = directory.decode('utf8')
    if isinstance(source_extension,bytesT): source_extension = source_extension.decode('utf8')
    if isinstance(sourcetext,bytesT): sourcetext = sourcetext.decode('utf8')
    if hasattr(name,'read'):
        sourcetext = name.read()
        name = getattr(name,'name',None)
        if not name: name = '_preppy_'+getMd5(sourcetext)
    else:
        # it's possible that someone could ask for
        #  name "subdir/spam.prep" in directory "/mydir", instead of
        #  "spam.prep" in directory "/mydir/subdir".  Failing to get
        # this right means getModule can fail to find it and recompile
        # every time.  This is common during batch compilation of directories.
        extraDir, name = os.path.split(name)
        if extraDir:
            if os.path.isabs(extraDir):
                directory = extraDir
            else:
                directory = directory + os.sep + extraDir
        dir = os.path.abspath(os.path.normpath(directory))

        # they may ask for 'spam.prep' instead of just 'spam'.  Trim off
        # any extension
        name = os.path.splitext(name)[0]
        if verbose:
            pnl('checking %s...' % os.path.join(dir, name))
        # savefile is deprecated but kept for safety.  savePy and savePyc are more
        # explicit and are the preferred.  By default it generates a pyc and no .py
        # file to reduce clutter.
        if savefile and savePyc == 0:
            savePyc = 1

    if sourcetext is not None:
        # they fed us the source explicitly
        sourcechecksum = getMd5(sourcetext)
        if not name: name = '_preppy_'+sourcechecksum
        if verbose: pnl("sourcetext provided...")
        sourcefilename = "<input text %s>" % name
        nosourcefile = 1
        module = SOURCE_MODULES.get(sourcetext,None)
        if module:
            return module
    else:
        nosourcefile = 0
        # see if the module exists as a python file
        sourcefilename = os.path.join(dir, name+source_extension)
        module = FILE_MODULES.get(sourcefilename,None)
        if module:
            return module

        try:
            module = rl_get_module(name,dir)
            module.__dict__['include'] = include
            module.__dict__['__preppy__vlhs__'] = __preppy__vlhs__
            if _globals:
                module.__dict__.update(_globals)
            checksum = module.__checksum__
            if verbose: pnl("found...")
        except: # ImportError:  #catch ALL Errors importing the module (eg name="")
            module = checksum = None
            if verbose: pnl(" py/pyc not found...")
            # check against source file
        try:
            sourcefile = open(sourcefilename, "r")
        except:
            if verbose: pnl("no source file, reuse...")
            if module is None:
                raise ValueError("couldn't find source %s or module %s" % (sourcefilename, name))
            # use the existing module??? (NO SOURCE PRESENT)
            FILE_MODULES[sourcefilename] = module
            return module
        else:
            sourcetext = sourcefile.read()
            # NOTE: force recompile on each new version of this module.
            sourcechecksum = getMd5(sourcetext)
            if sourcechecksum==checksum:
                if force==0:
                    # use the existing module. it matches
                    if verbose:
                        pnl("up to date.")
                    FILE_MODULES[sourcefilename] = module
                    return module
                else:
                    # always recompile
                    if verbose: pnl('forced recompile,')
            elif verbose:
                pnl("changed,")

    # if we got here we need to rebuild the module from source
    if verbose: pel("recompiling")
    global DIAGNOSTIC_FUNCTION
    DIAGNOSTIC_FUNCTION = None
    P = PreppyParser(sourcetext,sourcefilename,sourcechecksum)
    P.nosourcefile = nosourcefile
    P.compile(0)

    # default is compile to bytecode and save that.
    if savePyc:
        f = open(dir + os.sep + name + '.pyc','wb')
        P.dump(f)
        f.close()

    # now make a module
    from imp import new_module
    module = new_module(name)
    module.__dict__['include'] = include
    module.__dict__['__preppy__vlhs__'] = __preppy__vlhs__
    if _globals:
        module.__dict__.update(_globals)
    rl_exec(P.code,module.__dict__)
    if importModule:
        if nosourcefile:
            SOURCE_MODULES[sourcetext] = module
        else:
            FILE_MODULES[sourcefilename] = module
    return module

# support the old form here
getPreppyModule = getModule

####################################################################
#
#   utilities for compilation, setup scripts, housekeeping etc.
#
####################################################################
def installImporter():
    "This lets us import prep files directly"
    # the python import mechanics are only invoked if you call this,
    # since preppy has very few dependencies and I don't want to
    #add to them.
    from ihooks import ModuleLoader, ModuleImporter, install
    class PreppyLoader(ModuleLoader):
        "This allows prep files to be imported."

        def find_module_in_dir(self, name, dir, allow_packages=1):
            ModuleLoader = self.__class__.__bases__[0]
            stuff = ModuleLoader.find_module_in_dir(self, name, dir, allow_packages)
            if stuff:
                return stuff
            else:
                if dir:
                    prepFileName = dir + os.sep + name + '.prep'
                else:
                    prepFileName = name + '.prep'

                if os.path.isfile(prepFileName):
                    #compile WITHOUT IMPORTING to avoid triggering recursion
                    mod = compileModule(prepFileName, verbose=0, importModule=0)
                    #now use the default...
                    return ModuleLoader.find_module_in_dir(self, name, dir, allow_packages)
                else:
                    return None

    loader = PreppyLoader()
    importer = ModuleImporter(loader=loader)
    install(importer)

def uninstallImporter():
    import ihooks
    ihooks.uninstall()

def compileModule(fn, savePy=0, force=0, verbose=1, importModule=1):
    "Compile a prep file to a pyc file.  Optionally, keep the python source too."
    name, ext = os.path.splitext(fn)
    d = os.path.dirname(fn)
    return getModule(os.path.basename(name), directory=d, source_extension=ext,
                     savePyc=1, savePy=savePy, force=force,
                     verbose=verbose, importModule=importModule)

def compileModules(pattern, savePy=0, force=0, verbose=1):
    "Compile all prep files matching the pattern."
    import glob
    filenames = glob.glob(pattern)
    for filename in filenames:
        compileModule(filename, savePy, force, verbose)

from fnmatch import fnmatch
def compileDir(dirName, pattern="*.prep", recursive=1, savePy=0, force=0, verbose=1):
    "Compile all prep files in directory, recursively if asked"
    if verbose: pel('compiling directory %s' % dirName)
    if recursive:
        def _visit(A,D,N,pattern=pattern,savePy=savePy, verbose=verbose,force=force):
            for filename in filter(lambda fn,pattern=pattern: fnmatch(fn,pattern),
                    filter(os.path.isfile,map(lambda n, D=D: os.path.join(D,n),N))):
                compileModule(filename, savePy, force, verbose)
        os.path.walk(dirName,_visit,None)
    else:
        compileModules(os.path.join(dirName, pattern), savePy, force, verbose)

def _cleanFiles(filenames,verbose):
    for filename in filenames:
        if verbose:
            pnl('  found ' + filename + '; ')
        root, ext = os.path.splitext(os.path.abspath(filename))
        done = 0
        if os.path.isfile(root + '.py'):
            os.remove(root + '.py')
            done = done + 1
            if verbose: pnl(' removed .py ')
        if os.path.isfile(root + '.pyc'):
            os.remove(root + '.pyc')
            done = done + 1
            if verbose: pnl(' removed .pyc ')
        if done == 0:
            if verbose:
                pnl('nothing to remove')
        pel('')

def cleanDir(dirName, pattern="*.prep", recursive=1, verbose=1):
    "Removes all py and pyc files matching any prep files found"
    if verbose: pel('cleaning directory %s' % dirName)
    if recursive:
        def _visit(A,D,N,pattern=pattern,verbose=verbose):
            _cleanFiles(filter(lambda fn,pattern=pattern: fnmatch(fn,pattern),
                    filter(os.path.isfile,map(lambda n, D=D: os.path.join(D,n),N))),verbose)
        os.path.walk(dirName,_visit,None)
    else:
        import glob
        _cleanFiles(filter(os.path.isfile,glob.glob(os.path.join(dirName, pattern))),verbose)

def compileStuff(stuff, savePy=0, force=0, verbose=0):
    "Figures out what needs compiling"
    if os.path.isfile(stuff):
        compileModule(stuff, savePy=savePy, force=force, verbose=verbose)
    elif os.path.isdir(stuff):
        compileDir(stuff, savePy=savePy, force=force, verbose=verbose)
    else:
        compileModules(stuff, savePy=savePy, force=force, verbose=verbose)

def extractKeywords(arglist):
    "extracts a dictionary of keywords"
    d = {}
    for arg in arglist:
        chunks = arg.split('=')
        if len(chunks)==2:
            key, value = chunks
            d[key] = value
    return d

def _find_quoteValue(name,depth=2):
    try:
        while 1:
            g = sys._getframe(depth)
            if g.f_code.co_name=='__code__':
                g=g.f_globals
            else:
                g=g.f_locals
            if g.has_key(name): return g[name]
            depth += 1
    except:
        return None

def include(viewName,*args,**kwd):
    dir, filename = os.path.split(viewName)
    root, ext = os.path.splitext(filename)
    m = {}
    if dir: m['directory'] = dir
    if ext: m['source_extension'] = ext
    m = getModule(root,**m)
    if hasattr(m,'get'):
        #newstyle
        lquoter = quoter = None
        if kwd.has_key('__quoteFunc__'):
            quoter = kwd.pop('__quoteFunc__')
        elif kwd.has_key('quoteFunc'):
            quoter = kwd.pop('quoteFunc')
        if not quoter:
            quoter = _find_quoteValue('__quoteFunc__')
            if not quoter:
                quoter = _find_quoteValue('quoteFunc')
        if kwd.has_key('__lquoteFunc__'):
            lquoter = kwd.pop('__lquoteFunc__')
        if not lquoter:
            lquoter = _find_quoteValue('__lquoteFunc__')
            if not lquoter:
                lquoter = _find_quoteValue('quoteFunc')
        return m.get(__quoteFunc__=quoter or str,__lquoteFunc__=lquoter or str, *args,**kwd)
    else:
        #oldstyle
        if args:
            if len(args)>1:
                raise TypeError("include for old style prep file can have only one positional argument, dictionary")
            if kwd.has_key('dictionary'):
                raise TypeError('include: dictionary argument specified twice')
            dictionary = args(1).copy()
        elif kwd.has_key('dictionary'):
            dictionary = kwd.pop('dictionary').copy()
        else:
            dictionary = {}
        quoteFunc = None
        if kwd.has_key('quoteFunc'):
            quoteFunc = kwd.pop('quoteFunc')
        elif kwd.has_key('__quoteFunc__'):
            quoteFunc = kwd.pop('__quoteFunc__')
        if not quoteFunc:
            quoteFunc = _find_quoteValue('quoteFunc')
            if not quoteFunc:
                quoteFunc = _find_quoteValue('__quoteFunc__')
        dictionary.update(kwd)
        return m.getOutput(dictionary,quoteFunc=quoteFunc)

def main():
    if len(sys.argv)>1:
        name = sys.argv[1]

        if name == 'compile':
            names = sys.argv[2:]

            # save the intermediate python file
            if '--savepy' in names:
                names.remove('--savepy')
                savePy = 1
            elif '-p' in names:
                names.remove('-p')
                savePy = 1
            else:
                savePy = 0

            # force recompile every time
            if '--force' in names:
                names.remove('--force')
                force = 1
            elif '-f' in names:
                names.remove('-f')
                force = 1
            else:
                force = 0

            # extra output
            if '--verbose' in names:
                names.remove('--verbose')
                verbose = 1
            elif '-v' in names:
                names.remove('-v')
                verbose = 1
            else:
                verbose = 0

            for arg in names:
                compileStuff(arg, savePy=savePy, force=force, verbose=verbose)

        elif name == 'clean':
            for arg in sys.argv[2:]:
                cleanDir(arg, verbose=1)

        elif name == 'run':
            moduleName = sys.argv[2]
            params = extractKeywords(sys.argv)
            module = getPreppyModule(moduleName, verbose=0)
            module.run(params)

        else:
            #default is run
            moduleName = sys.argv[1]
            module = getPreppyModule(moduleName, verbose=0)
            if hasattr(module,'get'):
                pel(module.get())
            else:
                params = extractKeywords(sys.argv)
                module.run(params)
    else:
        pel("no argument: running tests")
        testgetOutput()
        pel(''); pel("PAUSING.  To continue hit return")
        raw_input("now: ")
        testgetmodule()

if __name__=="__main__":
    main()
