#copyright ReportLab Inc. 2000-2002
#see license.txt for license details
#history www.reportlab.co.uk/rl-cgi/viewcvs.cgi/rlextra/preppy/preppy.py
#$Header: /rl_home/xxx/repository/rlextra/preppy/preppy.py,v 1.22 2002/04/17 21:18:35 andy Exp $
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
 he module contains a run(...) function; you can pass in a dictionary of
parameters (such as the surname and amount parameters above), and optionally
an output stream or output-collection function if you don't want it to go to
standard output.

The command line options let you run modules with hand-input parameters -
useful for basic testing - and also to batch-compile or clean directories.
As with python scripts, it is a good idea to compile prep files on installation,
since unix applications may run as a different user and not have the needed
permission to store compiled modules.

"""

VERSION = 0.6


USAGE = """
The command line interface lets you test, compile and clean up:

    preppy modulename [arg1=value1, arg2=value2.....]
       - shorthand for 'preppy run ...', see below.

    preppy run modulename [arg1=value1, arg2=value2.....]
       - runs the module, optionally with arguments.  e.g.
         preppy.py flintstone.prep name=fred sex=m

    preppy.py compile module1[.prep] module2[.prep] module3 ...
       - compiles explicit modules

    preppy.py compile dirname1  dirname2 ...
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
UNESCAPES = ( (QSTARTDELIMITER, STARTDELIMITER), (QENDDELIMITER, ENDDELIMITER), (QUOTEQUOTE, QUOTE) )

import string
import os
import md5


def unescape(s, unescapes=UNESCAPES, r=string.replace):
    for (old, new) in unescapes:
        s = r(s, old, new)
    return s


"""
{{if x:}} this text $(endif}} that

becomes

if x:
    print (" this text"),
print (that\n")

note that extra spaces may be introduced compliments of print.
could change this to a file.write for more exact control...
"""

KEYWORDS = string.split("""
    if else elif for while script eval
    endif endfor endwhile
""")

def printstmt(txt, newline=1, linemax=40):
    """UNCLOSED call to __write__
       if everything is properly quoted you can append a % (x1, x2, x3)) onto the end of this"""
    # if all white return empty
    if not string.strip(txt):
        return ""
    lines = string.split(txt, "\n")
    out = []
    a = out.append
    start = 1
    while lines:
        l = lines[0]
        del lines[0]
        firstpass = 1
        while l or firstpass:
            firstpass=0
            l1 = l[:linemax]
            l = l[linemax:]
            if not l and lines:
                # paste back the newline
                l1 = l1+"\n"
            if start:
                a("__write__ (  (%s" % repr(l1))
                start = 0
            else:
                a("\t %s" % repr(l1))
    if not out:
        return "" # no write!
    out[-1] = out[-1] + " )"
    result = string.join(out, "\n")
    return result

def countnewlines(s):
    # make sure you get newlines at extremes
    s = ".%s." % s
    x = len(string.split(s, "\n"))
    if x: return x-1
    return 0

Substringquotes =[("%", "#P#"), ("(", "#[#"), (")", "#]#")]
for wc in string.whitespace:
    Substringquotes.append( (wc, "w."+repr(ord(wc))) )


def quotestring(s, cursor=0, lineno=None):
    """return a string where {{x}} becomes %(x)s and % becomes %(__percent__)s
       and also return a substitution dictionary for it containing
          __dict__ = {}
          __dict__["__percent__"] = "%"
          ...
          __dict__["x"] = x
          ...
       return the cursor where the process breaks (end or at {{if x:...}
       {{x}} x must not contain whitespace (except surrounding) but it can be (eg)
       math.sin(34.1) or dictionary.get("user","anonymous")
    """
    #print "quotestring at", cursor, repr(s[cursor:cursor+10])
    if lineno is None:
        #raise "oops"
        lineno = [0, "<top level>"]
    def diag(lineno=lineno):
        return "qs: near line %s at or after %s" % (lineno[0], repr(lineno[1]))
    global DIAGNOSTIC_FUNCTION
    DIAGNOSTIC_FUNCTION = diag
    from string import join, split, strip, find, replace
    slen = len(s)
    quotedparts = []
    #addpart = quotedparts.append
    def addpart(s, append=quotedparts.append, lineno=lineno):
        s = unescape(s) # unescape all text in output string
        append(s)
        if "\n" in s:
            lineno[0] = lineno[0] + countnewlines(s)
    dictlines = ["__dict__ = {}"]
    adddict = dictlines.append
    done = None
    starttaglen = len(STARTDELIMITER)
    endtaglen = len(ENDDELIMITER)
    dictassntemplate = "__dict__[%s] = %s # %s"
    key_seen = {}
    while done is None:
        findpercent = find(s, "%", cursor)
        if findpercent<0: findpercent = slen
        findstarttag = find(s, STARTDELIMITER, cursor)
        if findstarttag<0: findstarttag = slen
        findmin = min(findpercent, findstarttag)
        sclean = s[cursor:findmin]
        lineno[1] = s[findmin: findmin+10]
        addpart(sclean)
        #print "clean", repr(sclean)
        cursor = findmin
        if cursor==slen:
            done = 1
        elif s[cursor]=="%":
            cursor = cursor+1
            addpart("%(#percent#)s")
        else:
            # must be at start tag
            findendtag = find(s, ENDDELIMITER, cursor)
            savecursor = cursor
            cursor = cursor+starttaglen
            if findendtag<0:
                raise ValueError, "no end tag found after %s (%s)" % (repr(s[cursor-10:cursor+20]), diag())
            lineno[1] = s[savecursor: findendtag+10]
            block = s[cursor: findendtag]
            block = strip(block)
            if block[-1]==":":
                blockx = block[:-1]
            else:
                blockx = block
            blockx = split(blockx)[0]
            #if complexdirective(block) or # disabled to allow complex expressions
            #print "blockx", blockx
            if blockx in KEYWORDS:
                cursor = savecursor
                done = 1 # can't handle more complex things here
            else:
                cursor = findendtag+endtaglen
                sblock = block
                # unescape the block, and the sblock...
                sblock = block = unescape(block)
                # quote sblock for substitution format
                for (c, rc) in Substringquotes:
                    if c in sblock:
                        sblock = replace(sblock, c, rc)
                # test the syntax of the block
                try:
                    test = compile(block, "<string>", "eval")
                except:
                    raise ValueError, "bad expression (after unescape): " + repr(block)
                # optimization: don't recompute substitutions already seen
                if not key_seen.has_key(sblock):
                    substitutionline = dictassntemplate % (repr(sblock), block, repr(s[savecursor:cursor+10]))
                    adddict(substitutionline)
                    key_seen[sblock] = block
                stringsub = "%s(%s)s" % ("%", sblock)
                addpart(stringsub)
    percentline = dictassntemplate % (repr("#percent#"), repr("%"), "required percent sub")
    adddict(percentline)
    quotestring = join(quotedparts, "")
    dictstring = join(dictlines, "\n")
    #print "==== dictstring"
    #print dictstring
    #print "==== quotestring"
    #print quotestring
    return (quotestring, dictstring, cursor)

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
"""

"""
# test code for quotestring
(qs, ds, c) = quotestring(teststring, cursor=0)
print "---------quoted to ", c, `teststring[c:c+20]`
print qs
print "---------dict string"
print ds
"""


#### standard code templates

TOPLEVELWRAPPER = """\
### begin standard prologue
import sys
__save_sys_stdout__ = sys.stdout
try: # compiled logic below
%s
finally: #### end of compiled logic, standard cleanup
    import sys # for safety
    #print "resetting stdout", sys.stdout, "to", __save_sys_stdout__
    sys.stdout = __save_sys_stdout__
"""

TOPLEVELPROLOG = """\
### top level prologue
# redirect stdout, maybe
try:
    # if outputfile is defined, blindly assume it supports file protocol, reset sys.stdout
    if outputfile is None:
        raise NameError
    stdout = sys.stdout = outputfile
except NameError:
    stdout = sys.stdout
    outputfile = None
# make sure __write__ is defined
try:
    if __write__ is None:
        raise NameError
    if outputfile and __write__:
        raise ValueError, "do not define both outputfile (%s) and __write__ (%s)." %(outputfile, __write__)
except NameError:
    __write__ = stdout.write
# now exec the assignments in the dictionary
try:
    __d__ = dictionary
except:
    pass
else:
    for __n__ in __d__.keys():
        __forbidden__ = 0 # paranoid security check: disallow complex python L-expressions...
        for __c__ in ".([{": # no function calls, lists, attributes, dicts, etc.
            if __c__ in __n__:
                __forbidden__ = 1
        if not __forbidden__:
            try:
                exec("%s=__d__[%s]") % (__n__, repr(__n__)) in locals()
            except:
                pass # ignore dict entries that aren't valid variable names
### end of standard prologues
"""

class PreProcessor:
    #STARTDELIMITER = STARTDELIMITER # NOT USED, USE MODULE GLOBAL
    #ENDDELIMITER = ENDDELIMITER
    indentstring = "\t"
    def indent(self, s, indentstring=None):
        if indentstring is None:
            indentstring = self.indentstring
        return indentstring + string.replace(s, "\n", "\n"+indentstring)

    def __call__(self, inputtext, cursor=0, toplevel=1, lineno=None):
        # go to end of string (if toplevel) or dedent token (if not toplevel)
        #print "call at", cursor, repr(inputtext[cursor:cursor+10])
        if lineno is None:
            if not toplevel:
                raise "internal error", "lineno should be initialized!"
            lineno = [0, "<toplevel>"]
        def diag(lineno=lineno):
            return "pp: near line %s at or after %s" % (lineno[0], repr(lineno[1]))
        global DIAGNOSTIC_FUNCTION
        DIAGNOSTIC_FUNCTION = diag
        if toplevel:
            outputlist = [TOPLEVELPROLOG]
        else:
            outputlist = []
        a = outputlist.append
        #def a(s, outputlist=outputlist):
        #    "debug version"
        #    print "    ===== adding"
        #    print s
        #    outputlist.append(s)
        from string import strip, join, find
        done = None
        inputlen = len(inputtext)
        while done is None:
            # do a print statement for stuff before a complex directive
            #print "iterating at", cursor, repr(inputtext[cursor:cursor+10])
            (quoted, dictstring, newcursor) = quotestring(inputtext, cursor, lineno)
            segment = inputtext[cursor: newcursor]
            if "%" in quoted:
                a(dictstring)
                prints = printstmt(quoted) + " % __dict__ )" # note comma!
            else:
                segment = unescape(segment)
                prints = printstmt(segment)
                if prints:
                    # close it
                    prints = prints + ")"
                else:
                    prints = "pass"
            a(prints)
            cursor = newcursor
            if cursor>=inputlen:
                done = 1
            else:
                # should be at a complex directive
                (startblock, block, sblock, newcursor) = self.getDirectiveBlock(cursor, inputtext, lineno)
                if newcursor==cursor:
                    raise ValueError, "no progress in getdirectiveblock"
                oldcursor = cursor
                cursor = newcursor
                lineno[1] = inputtext[startblock: startblock+20]
                # now test for constructs
                if find(sblock, "if") == 0:
                    #print "in if"
                    # if statement, first add the block line
                    check_condition("if", sblock)
                    sblock = proctologist(sblock)
                    a(sblock)
                    # then get the conditional block
                    (conditional, cursor) = self(inputtext, cursor, toplevel=0, lineno=lineno)
                    iconditional = self.indent(conditional)
                    a(iconditional)
                    inif = 1
                    while inif:
                        # now we should be at an else elif or endif
                        if find(inputtext, STARTDELIMITER, cursor)!=cursor:
                            raise ValueError, "not at starttag"
                        (startblock, block, sblock, cursor) = self.getDirectiveBlock(cursor, inputtext, lineno)
                        if find(sblock, "else")==0:
                            if complexdirective(block):
                                raise ValueError, "bad else? %s" %repr(sblock)
                            #check_condition("else", sblock)
                            sblock = proctologist(sblock)
                            a(sblock)
                            (conditional, cursor) = self(inputtext, cursor, toplevel=0, lineno=lineno)
                            iconditional = self.indent(conditional)
                            a(iconditional)
                            # MUST be at endif
                            inif = 0
                            (startblock, block, sblock, cursor) = self.getDirectiveBlock(cursor, inputtext, lineno)
                            if find(sblock, "endif")!=0:
                                raise ValueError, "else not followed by endif %s.%s" % (
                                    repr(inputtext[startblock-10:startblock]), repr(inputtext[startblock:startblock+10]))
                            if complexdirective(block):
                                raise ValueError, "bad endif? %s" %repr(sblock)
                        elif find(sblock, "elif")==0:
                            check_condition("elif", sblock)
                            sblock = proctologist(sblock)
                            a(sblock)
                            (conditional, cursor) = self(inputtext, cursor, toplevel=0, lineno=lineno)
                            iconditional = self.indent(conditional)
                            a(iconditional)
                        elif find(sblock, "endif")==0:
                            #print "saw endif"
                            inif = 0
                elif find(sblock, "while") == 0 or find(sblock, "for")==0:
                    if find(sblock, "while") == 0:
                        directive="while"
                    elif find(sblock, "for")==0:
                        directive="for"
                    check_condition(directive, sblock)
                    sblock = proctologist(sblock)
                    #print "in", directive
                    # while statement
                    a(sblock)
                    # then get the conditional block
                    (conditional, cursor) = self(inputtext, cursor, toplevel=0, lineno=lineno)
                    iconditional = self.indent(conditional)
                    a(iconditional)
                    (startblock, block, sblock, cursor) = self.getDirectiveBlock(cursor, inputtext, lineno)
                    if find(sblock, "end"+directive)!=0:
                        raise ValueError, "%s not followed by end%s %s.%s" % (directive, directive,
                            repr(inputtext[startblock-10:startblock]), repr(inputtext[startblock:startblock+10]))
                    if complexdirective(block):
                        raise ValueError, "bad end marker? %s" %repr(block)
                    #print "... done with", directive
##                elif find(sblock, "script")==0:
##                    # include literal code, indented properly
##                    # strip out script tag
##                    fscript = find(block, "script")
##                    ddblock = block[fscript+len("script"):]
##                    ddblock = dedent(ddblock)
##                    #print "... dedented script"
##                    #print ddblock
##                    a(ddblock)
                elif find(sblock, "script")==0 or find(sblock, "eval")==0:
                    if strip(sblock)=="eval":
                        mode = "eval"
                        compilemode = "eval"
                    elif strip(sblock)!="script":
                        raise ValueError, "bad script or eval tag: "+repr(sblock)
                    else:
                        mode = "script"
                        compilemode = "exec"
                    # look for endscript
                    #print "modes", mode, compilemode
                    endtag = "%send%s%s" % (STARTDELIMITER, mode, ENDDELIMITER)
                    endlocation = find(inputtext, endtag, cursor)
                    if endlocation<cursor:
                        raise ValueError, "can't find %s after script start" % repr(endtag)
                    ddblock = inputtext[cursor:endlocation]
                    ddblock = dedent(ddblock)
                    ddblock = unescape(ddblock)
                    import sys
                    try:
                        test = compile(ddblock, "<string>", compilemode)
                    except:
                        t,v,tb = sys.exc_type, sys.exc_value, sys.exc_traceback
                        import traceback
                        tb = traceback.format_tb(tb)
                        tb = string.join(tb, "\n")
                        # how to get the line in the script for the error?
                        raise ValueError, "bad script code for %s\n%s\n\n%s\n%s\n%s" % (
                            compilemode, ddblock, t, v, tb)
                    if mode=="script":
                        a(ddblock)
                    elif mode=="eval":
                        code = "__write__(str(%s))" % ddblock
                        a(code)
                    cursor = endlocation + len(endtag)
                elif not toplevel:
                    # assume the calling routine understands the directive
                    #print "defaulting to return"
                    cursor = oldcursor
                    done = 1
                    continue
                else:
                    raise ValueError, "at toplevel don't understand directive %s.%s" % (
                        repr(inputtext[startblock-10:startblock]), repr(inputtext[startblock:startblock+10]))
        output = join(outputlist, "\n")
        if toplevel:
            output = self.indent(output)
            output = TOPLEVELWRAPPER % output
        return (output, cursor)

    def getDirectiveBlock(self, cursor, inputtext, lineno=None):
        #print repr((inputtext[cursor], inputtext[cursor:cursor+20]))
        if lineno is None: lineno = [0]
        from string import find, strip
        starttaglen = len(STARTDELIMITER)
        endtaglen = len(ENDDELIMITER)
        # should be at a starttag
        newcursor = cursor+starttaglen
        if inputtext[cursor:newcursor]!=STARTDELIMITER:
                    raise ValueError, "no start tag found at %s.%s" % (
                        repr(inputtext[cursor-10:cursor]), repr(inputtext[cursor:cursor+10]))
        cursor = newcursor
        findendtag = find(inputtext, ENDDELIMITER, cursor)
        if findendtag<cursor:
                    raise ValueError, "no end tag found after %s.%s" % (
                        repr(inputtext[cursor-10:cursor]), repr(inputtext[cursor:cursor+10]))
        startblock = cursor
        endblock = findendtag
        block = inputtext[startblock:endblock]
        if "\n" in block:
            lineno[0] = lineno[0] + countnewlines(block)
        cursor = endblock+endtaglen
        sblock = unescape(strip(block))
        return (startblock, block, sblock, cursor)

    def module_source(self, string):
        """make a module with a function run(dictionary) which executes the interpreted string"""
        (out, c) = self(string)
        iout = self.indent(out)
        result = module_source_template % iout
        return result

def proctologist(s):
    """now bend over turn your head and cough"""
    # check the colon
    s = string.strip(s)
    if s[-1]!=":":
        # the following dommented to allow x[5:8] in for statements for example.
        #if ":" in s:
        #    raise ValueError, repr(s)+" contains bogus colon"
        s = s+":"
    return s

def check_condition(keyword, block):
    "for example in 'if cond:' make sure the condition compiles"
    block = string.strip(block)
    if block[-1]==":":
        block = block[:-1]
    lk = len(keyword)
    if block[:lk]!=keyword:
        raise ValueError, "bad call to check_condition "+repr((block, keyword))
    block = string.strip(block[lk:])
    try:
        test = compile(block, "<string>", "eval")
    except:
        raise ValueError, "bad %s expression: %s" % (keyword, repr(block))

def complexdirective(s):
    from string import split, strip
    return len(split(strip(s))) != 1

def dedent(text):
    """get rid of redundant indentation in text
       this dedenter IS NOT smart about converting tabs to spaces!!!"""
    from string import split, find, strip, join
    lines = split(text, "\n")
    # omit empty lines
    while lines and not strip(lines[0]):
        del lines[0]
    if not lines:
        return "" # completely white
    line0 = lines[0]
    sline0 = strip(line0)
    ssline0 = split(sline0)
    firstword = ssline0[0]
    findfirstword = find(line0, firstword)
    if findfirstword<0:
        raise "huh?"
    indent = line0[:findfirstword]
    linesout = []
    for l in lines:
        if not strip(l):
            linesout.append("")
            continue
        lindent = l[:findfirstword]
        if lindent!=indent:
            raise ValueError, "inconsistent indent expected %s got %s in %s" % (repr(indent), repr(lindent), l)
        linesout.append(l[findfirstword:])
    return join(linesout, "\n")

module_source_template = """
def run(dictionary, __write__=None, outputfile=None):
%s

if __name__=="__main__":
    run({})
"""

def parsetest():
    fn = "./testoutput.py"
    P = PreProcessor()
    (out, c) = P(teststring)
    print "generated", len(out), "bytes from", c, "input"
    print "generating file", fn
    f = open(fn, "w")
    import sys
    stdout = sys.stdout
    sys.stdout = f
    print out
    sys.stdout = stdout
    print "wrote", fn

def testgetmodule(name="testpreppy"):
    name = "testpreppy"
    print "trying to load", name
    result = getPreppyModule(name, verbose=1)
    print "load successful! running result"
    print "=" * 100
    result.run({})

# cache found modules by source file name
GLOBAL_LOADED_MODULE_DICTIONARY = {}

def getModule(name,
              directory=".",
              source_extension=".prep",
              verbose=0,
              savefile=None,
              sourcetext=None,
              savePy=0,
              savePyc=1):
    """Returns a python module implementing the template.  This will be
    recompiled from source if needed."""


    # it's possible that someone could ask for
    #  name "subdir/spam.prep" in directory "/mydir", instead of
    #  "spam.prep" in directory "/mydir/subdir".  Failing to get
    # this right means getModule can fail to find it and recompile
    # every time.  This is common during batch compilation of directories.
    extraDir, name = os.path.split(name)
    if extraDir:
        directory = directory + os.sep + extraDir
    directory = os.path.normpath(directory)

    # they may ask for 'spam.prep' instead of just 'spam'.  Trim off
    # any extension
    name = os.path.splitext(name)[0]
    if verbose:
        print ('checking %s/%s...' % (directory, name)),
    # savefile is deprecated but kept for safety.  savePy and savePyc are more
    # explicit and are the preferred.  By default it generates a pyc and no .py
    # file to reduce clutter.
    if savefile and savePyc == 0:
        savePyc = 1


    if sourcetext is not None:
        # they fed us the source explicitly
        if verbose: print "sourcetext provided...",
        sourcefilename = "<input text %s>" % name
        sourcechecksum = md5.new(sourcetext + repr(VERSION)).digest()
        savePy = 0 # cannot savefile if source file provided
        savePyc = 0
    else:
        # see if the module exists as a python file
        from sys import path
        sourcefilename = os.path.join(directory, name+source_extension)
        if GLOBAL_LOADED_MODULE_DICTIONARY.has_key(sourcefilename):
            return GLOBAL_LOADED_MODULE_DICTIONARY[sourcefilename]
        if directory not in path:
            path.insert(0, directory)
        try:
            module = __import__(name)
            checksum = module.__checksum__
            if verbose: print "found...",
        except: # ImportError:  catch ALL Errors importing the module (eg name="")
            module = checksum = None
            if verbose: print " py/pyc not found...",
            # check against source file
        try:
            sourcefile = open(sourcefilename, "r")
        except:
            if verbose: print "no source file, reuse...",
            if module is None:
                raise ValueError, "couldn't find source %s or module %s" % (sourcefilename, name)
            # use the existing module??? (NO SOURCE PRESENT)
            GLOBAL_LOADED_MODULE_DICTIONARY[sourcefilename] = module
            return module
        else:
            sourcetext = sourcefile.read()
            # NOTE: force recompile on each new version of this module.
            sourcechecksum = md5.new(sourcetext + repr(VERSION)).digest()
            if sourcechecksum==checksum:
                # use the existing module. it matches
                if verbose: print "up to date."
                GLOBAL_LOADED_MODULE_DICTIONARY[sourcefilename] = module
                return module
            elif verbose:
                print "changed,",
    # if we got here we need to rebuild the module from source
    if verbose:
        print "recompiling"
    P = PreProcessor()
    global DIAGNOSTIC_FUNCTION
    DIAGNOSTIC_FUNCTION = None
    import sys
    sourcetext = cleantext(sourcetext) # get rid of gunk in newlines, just in case
    try:
        out = P.module_source(sourcetext)
    except:
        t,v,tb = sys.exc_type, sys.exc_value, sys.exc_traceback
        import traceback
        tb = traceback.format_tb(tb)
        tb = string.join(tb, "\n")
        print "ERROR PROCESSING PREPPY FILE TRACEBACK"
        print tb
        print "Type", t
        print "Value", v
        if DIAGNOSTIC_FUNCTION:
            print "LAST DIAGNOSTIC:"
            print DIAGNOSTIC_FUNCTION()
        else:
            print "no further diagnostic available"
        print "ERROR PROCESSING PREPPY FILE"
        sys.exit(1)

    # generate the python source in memory as if it was a py file.
    # then save to py and pyc as specified.
    pythonFileName = name + '.py'
    pythonSource = """
'''
PREPPY MODULE %s
Automatically generated file from preprocessor source %s
DO NOT EDIT!
'''
__checksum__ = %s
%s
""" % (name, pythonFileName, repr(sourcechecksum), out)

    # default is not to save source.
    if savePy:
        srcFileName = os.path.join(directory, pythonFileName)
    else:
        import tempfile
        srcFileName = tempfile.mktemp()
    open(srcFileName, 'w').write(pythonSource)

    # default is compile to bytecode and save that.
    if savePyc:
        import py_compile

        py_compile.compile(srcFileName,
                           cfile=directory + os.sep + name + '.pyc',
                           dfile=name + '.py')


    if not savePy:
        os.remove(srcFileName)

    # now make a module
    from imp import new_module
    result = new_module(name)
    exec out in result.__dict__
    GLOBAL_LOADED_MODULE_DICTIONARY[sourcefilename] = result
    return result

def cleantext(text):
    ### THIS GETS RID OF EXTRA WHITESPACE AT THE END OF LINES (EG CR'S)
    textlines = string.split(text, "\n")
    for i in range(len(textlines)):
        l = textlines[i]
        l1 = "."+l
        l2 = string.strip(l1)
        l3 = l2[1:]
        textlines[i] = l3
    return string.join(textlines, "\n")

# support the old form here
getPreppyModule = getModule


    ####################################################################
    #
    #   utilities for setup scripts, housekeeping etc.
    #
    ####################################################################

def compileModule(prepFileName, savePy=0, verbose=1):
    "Compile a prep file to a pyc file.  Optionally, keep the python source too."
    name, ext = os.path.splitext(prepFileName)
    m = getModule(name, source_extension=ext, savePyc=1, savePy=savePy, verbose=verbose)

def compileModules(pattern, savePy=0, verbose=1):
    "Compile all prep files matching the pattern.  Helps win32 which has to do its own globbing"
    import glob
    filenames = glob.glob(pattern)
    for filename in filenames:
        compileModule(filename, savePy, verbose)

from fnmatch import fnmatch
def compileDir(dirName, pattern="*.prep", recursive=1, savePy=0, verbose=1):
    "Compile all prep files in directory, recursively if asked"
    if verbose: print 'compiling directory %s' % dirName
    if recursive:
        def _visit(A,D,N,pattern=pattern,savePy=savePy, verbose=verbose):
            for filename in filter(lambda fn,pattern=pattern: fnmatch(fn,pattern),
                    filter(os.path.isfile,map(lambda n, D=D: os.path.join(D,n),N))):
                compileModule(filename, savePy, verbose)
        os.path.walk(dirName,_visit,None)
    else:
        compileModules(os.path.join(dirName, pattern), savePy, verbose)

def _cleanFiles(filenames,verbose):
    for filename in filenames:
        if verbose:
            print '  found ' + filename + '; ',
        root, ext = os.path.splitext(os.path.abspath(filename))
        done = 0
        if os.path.isfile(root + '.py'):
            os.remove(root + '.py')
            done = done + 1
            if verbose: print ' removed .py ',
        if os.path.isfile(root + '.pyc'):
            os.remove(root + '.pyc')
            done = done + 1
            if verbose: print ' removed .pyc ',
        if done == 0:
            if verbose:
                print 'nothing to remove',
        print

def cleanDir(dirName, pattern="*.prep", recursive=1, verbose=1):
    "Removes all py and pyc files matching any prep files found"
    if verbose: print 'cleaning directory %s' % dirName
    if recursive:
        def _visit(A,D,N,pattern=pattern,verbose=verbose):
            _cleanFiles(filter(lambda fn,pattern=pattern: fnmatch(fn,pattern),
                    filter(os.path.isfile,map(lambda n, D=D: os.path.join(D,n),N))),verbose)
        os.path.walk(dirName,_visit,None)
    else:
        import glob
        _cleanFiles(filter(os.path.isfile,glob.glob(os.path.join(dirName, pattern))),verbose)

def compileStuff(stuff):
    "Figures out what needs compiling"
    if os.path.isfile(stuff):
        compileModule(stuff)
    elif os.path.isdir(stuff):
        compileDir(stuff)
    else:
        compileModules(stuff)

def extractKeywords(arglist):
    "extracts a dictionary of keywords"
    d = {}
    for arg in arglist:
        chunks = string.split(arg, '=')
        if len(chunks)==2:
            key, value = chunks
            d[key] = value
    return d

def main():
    import sys
    if len(sys.argv)>1:
        name = sys.argv[1]
        if name == 'compile':
            for arg in sys.argv[2:]:
                compileStuff(arg)
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
            params = extractKeywords(sys.argv)
            module = getPreppyModule(moduleName, verbose=0)
            module.run(params)
    else:
        print "no argument: running tests"
        parsetest()
        print; print "PAUSING.  To continue hit return"
        raw_input("now: ")
        testgetmodule()

if __name__=="__main__":
    main()
