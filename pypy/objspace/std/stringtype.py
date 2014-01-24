from sys import maxint

from rpython.rlib import jit
from rpython.rlib.objectmodel import newlist_hint, resizelist_hint, specialize

from pypy.interpreter.gateway import interp2app, unwrap_spec, WrappedDefault
from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.objspace.std.stdtypedef import StdTypeDef, SMM
from pypy.objspace.std.register_all import register_all

def wrapstr(space, s):
    from pypy.objspace.std.stringobject import W_StringObject
    if space.config.objspace.std.sharesmallstr:
        if space.config.objspace.std.withprebuiltchar:
            # share characters and empty string
            if len(s) <= 1:
                if len(s) == 0:
                    return W_StringObject.EMPTY
                else:
                    s = s[0]     # annotator hint: a single char
                    return wrapchar(space, s)
        else:
            # only share the empty string
            if len(s) == 0:
                return W_StringObject.EMPTY
    return W_StringObject(s)

def wrapchar(space, c):
    from pypy.objspace.std.stringobject import W_StringObject
    if space.config.objspace.std.withprebuiltchar and not jit.we_are_jitted():
        return W_StringObject.PREBUILT[ord(c)]
    else:
        return W_StringObject(c)

def sliced(space, s, start, stop, orig_obj):
    assert start >= 0
    assert stop >= 0
    if start == 0 and stop == len(s) and space.is_w(space.type(orig_obj), space.w_str):
        return orig_obj
    return wrapstr(space, s[start:stop])

def joined2(space, str1, str2):
    if space.config.objspace.std.withstrbuf:
        from pypy.objspace.std.strbufobject import joined2
        return joined2(str1, str2)
    else:
        return wrapstr(space, str1 + str2)

str_join    = SMM('join', 2,
                  doc='S.join(sequence) -> string\n\nReturn a string which is'
                      ' the concatenation of the strings in the\nsequence. '
                      ' The separator between elements is S.')
str_split   = SMM('split', 3, defaults=(None,-1),
                  doc='S.split([sep [,maxsplit]]) -> list of strings\n\nReturn'
                      ' a list of the words in the string S, using sep as'
                      ' the\ndelimiter string.  If maxsplit is given, at most'
                      ' maxsplit\nsplits are done. If sep is not specified or'
                      ' is None, any\nwhitespace string is a separator.')
str_rsplit  = SMM('rsplit', 3, defaults=(None,-1),
                  doc='S.rsplit([sep [,maxsplit]]) -> list of'
                      ' strings\n\nReturn a list of the words in the string S,'
                      ' using sep as the\ndelimiter string, starting at the'
                      ' end of the string and working\nto the front.  If'
                      ' maxsplit is given, at most maxsplit splits are\ndone.'
                      ' If sep is not specified or is None, any whitespace'
                      ' string\nis a separator.')
str_isdigit    = SMM('isdigit', 1,
                     doc='S.isdigit() -> bool\n\nReturn True if all characters'
                         ' in S are digits\nand there is at least one'
                         ' character in S, False otherwise.')
str_isalpha    = SMM('isalpha', 1,
                     doc='S.isalpha() -> bool\n\nReturn True if all characters'
                         ' in S are alphabetic\nand there is at least one'
                         ' character in S, False otherwise.')
str_isspace    = SMM('isspace', 1,
                     doc='S.isspace() -> bool\n\nReturn True if all characters'
                         ' in S are whitespace\nand there is at least one'
                         ' character in S, False otherwise.')
str_isupper    = SMM('isupper', 1,
                     doc='S.isupper() -> bool\n\nReturn True if all cased'
                         ' characters in S are uppercase and there is\nat'
                         ' least one cased character in S, False otherwise.')
str_islower    = SMM('islower', 1,
                     doc='S.islower() -> bool\n\nReturn True if all cased'
                         ' characters in S are lowercase and there is\nat'
                         ' least one cased character in S, False otherwise.')
str_istitle    = SMM('istitle', 1,
                     doc='S.istitle() -> bool\n\nReturn True if S is a'
                         ' titlecased string and there is at least'
                         ' one\ncharacter in S, i.e. uppercase characters may'
                         ' only follow uncased\ncharacters and lowercase'
                         ' characters only cased ones. Return'
                         ' False\notherwise.')
str_isalnum    = SMM('isalnum', 1,
                     doc='S.isalnum() -> bool\n\nReturn True if all characters'
                         ' in S are alphanumeric\nand there is at least one'
                         ' character in S, False otherwise.')
str_ljust      = SMM('ljust', 3, defaults=(' ',),
                     doc='S.ljust(width[, fillchar]) -> string\n\nReturn S'
                         ' left justified in a string of length width. Padding'
                         ' is\ndone using the specified fill character'
                         ' (default is a space).')
str_rjust      = SMM('rjust', 3, defaults=(' ',),
                     doc='S.rjust(width[, fillchar]) -> string\n\nReturn S'
                         ' right justified in a string of length width.'
                         ' Padding is\ndone using the specified fill character'
                         ' (default is a space)')
str_upper      = SMM('upper', 1,
                     doc='S.upper() -> string\n\nReturn a copy of the string S'
                         ' converted to uppercase.')
str_lower      = SMM('lower', 1,
                     doc='S.lower() -> string\n\nReturn a copy of the string S'
                         ' converted to lowercase.')
str_swapcase   = SMM('swapcase', 1,
                     doc='S.swapcase() -> string\n\nReturn a copy of the'
                         ' string S with uppercase characters\nconverted to'
                         ' lowercase and vice versa.')
str_capitalize = SMM('capitalize', 1,
                     doc='S.capitalize() -> string\n\nReturn a copy of the'
                         ' string S with only its first'
                         ' character\ncapitalized.')
str_title      = SMM('title', 1,
                     doc='S.title() -> string\n\nReturn a titlecased version'
                         ' of S, i.e. words start with uppercase\ncharacters,'
                         ' all remaining cased characters have lowercase.')
str_find       = SMM('find', 4, defaults=(0, maxint),
                     doc='S.find(sub [,start [,end]]) -> int\n\nReturn the'
                         ' lowest index in S where substring sub is'
                         ' found,\nsuch that sub is contained within'
                         ' s[start,end].  Optional\narguments start and end'
                         ' are interpreted as in slice notation.\n\nReturn -1'
                         ' on failure.')
str_rfind      = SMM('rfind', 4, defaults=(0, maxint),
                     doc='S.rfind(sub [,start [,end]]) -> int\n\nReturn the'
                         ' highest index in S where substring sub is'
                         ' found,\nsuch that sub is contained within'
                         ' s[start,end].  Optional\narguments start and end'
                         ' are interpreted as in slice notation.\n\nReturn -1'
                         ' on failure.')
str_partition  = SMM('partition', 2,
                     doc='S.partition(sep) -> (head, sep, tail)\n\nSearches'
                         ' for the separator sep in S, and returns the part before'
                         ' it,\nthe separator itself, and the part after it.  If'
                         ' the separator is not\nfound, returns S and two empty'
                         ' strings.')
str_rpartition = SMM('rpartition', 2,
                     doc='S.rpartition(sep) -> (tail, sep, head)\n\nSearches'
                         ' for the separator sep in S, starting at the end of S,'
                         ' and returns\nthe part before it, the separator itself,'
                         ' and the part after it.  If the\nseparator is not found,'
                         ' returns two empty strings and S.')
str_index      = SMM('index', 4, defaults=(0, maxint),
                     doc='S.index(sub [,start [,end]]) -> int\n\nLike S.find()'
                         ' but raise ValueError when the substring is not'
                         ' found.')
str_rindex     = SMM('rindex', 4, defaults=(0, maxint),
                     doc='S.rindex(sub [,start [,end]]) -> int\n\nLike'
                         ' S.rfind() but raise ValueError when the substring'
                         ' is not found.')
str_replace    = SMM('replace', 4, defaults=(-1,),
                     doc='S.replace (old, new[, count]) -> string\n\nReturn a'
                         ' copy of string S with all occurrences of'
                         ' substring\nold replaced by new.  If the optional'
                         ' argument count is\ngiven, only the first count'
                         ' occurrences are replaced.')
str_zfill      = SMM('zfill', 2,
                     doc='S.zfill(width) -> string\n\nPad a numeric string S'
                         ' with zeros on the left, to fill a field\nof the'
                         ' specified width.  The string S is never truncated.')
str_strip      = SMM('strip',  2, defaults=(None,),
                     doc='S.strip([chars]) -> string or unicode\n\nReturn a'
                         ' copy of the string S with leading and'
                         ' trailing\nwhitespace removed.\nIf chars is given'
                         ' and not None, remove characters in chars'
                         ' instead.\nIf chars is unicode, S will be converted'
                         ' to unicode before stripping')
str_rstrip     = SMM('rstrip', 2, defaults=(None,),
                     doc='S.rstrip([chars]) -> string or unicode\n\nReturn a'
                         ' copy of the string S with trailing whitespace'
                         ' removed.\nIf chars is given and not None, remove'
                         ' characters in chars instead.\nIf chars is unicode,'
                         ' S will be converted to unicode before stripping')
str_lstrip     = SMM('lstrip', 2, defaults=(None,),
                     doc='S.lstrip([chars]) -> string or unicode\n\nReturn a'
                         ' copy of the string S with leading whitespace'
                         ' removed.\nIf chars is given and not None, remove'
                         ' characters in chars instead.\nIf chars is unicode,'
                         ' S will be converted to unicode before stripping')
str_center     = SMM('center', 3, defaults=(' ',),
                     doc='S.center(width[, fillchar]) -> string\n\nReturn S'
                         ' centered in a string of length width. Padding'
                         ' is\ndone using the specified fill character'
                         ' (default is a space)')
str_count      = SMM('count', 4, defaults=(0, maxint),
                     doc='S.count(sub[, start[, end]]) -> int\n\nReturn the'
                         ' number of occurrences of substring sub in'
                         ' string\nS[start:end].  Optional arguments start and'
                         ' end are\ninterpreted as in slice notation.')
str_endswith   = SMM('endswith', 4, defaults=(0, maxint),
                     doc='S.endswith(suffix[, start[, end]]) -> bool\n\nReturn'
                         ' True if S ends with the specified suffix, False'
                         ' otherwise.\nWith optional start, test S beginning'
                         ' at that position.\nWith optional end, stop'
                         ' comparing S at that position.')
str_expandtabs = SMM('expandtabs', 2, defaults=(8,),
                     doc='S.expandtabs([tabsize]) -> string\n\nReturn a copy'
                         ' of S where all tab characters are expanded using'
                         ' spaces.\nIf tabsize is not given, a tab size of 8'
                         ' characters is assumed.')
str_splitlines = SMM('splitlines', 2, defaults=(0,),
                     doc='S.splitlines([keepends]) -> list of'
                         ' strings\n\nReturn a list of the lines in S,'
                         ' breaking at line boundaries.\nLine breaks are not'
                         ' included in the resulting list unless keepends\nis'
                         ' given and true.')
str_startswith = SMM('startswith', 4, defaults=(0, maxint),
                     doc='S.startswith(prefix[, start[, end]]) ->'
                         ' bool\n\nReturn True if S starts with the specified'
                         ' prefix, False otherwise.\nWith optional start, test'
                         ' S beginning at that position.\nWith optional end,'
                         ' stop comparing S at that position.')
str_translate  = SMM('translate', 3, defaults=('',), #unicode mimic not supported now
                     doc='S.translate(table [,deletechars]) -> string\n\n'
                         'Return a copy of the string S, where all characters'
                         ' occurring\nin the optional argument deletechars are'
                         ' removed, and the\nremaining characters have been'
                         ' mapped through the given\ntranslation table, which'
                         ' must be a string of length 256.')
str_decode     = SMM('decode', 3, defaults=(None, None),
                     argnames=['encoding', 'errors'],
                     doc='S.decode([encoding[,errors]]) -> object\n\nDecodes S'
                         ' using the codec registered for encoding. encoding'
                         ' defaults\nto the default encoding. errors may be'
                         ' given to set a different error\nhandling scheme.'
                         " Default is 'strict' meaning that encoding errors"
                         ' raise\na UnicodeDecodeError. Other possible values'
                         " are 'ignore' and 'replace'\nas well as any other"
                         ' name registerd with codecs.register_error that'
                         ' is\nable to handle UnicodeDecodeErrors.')

register_all(vars(), globals())

# ____________________________________________________________

def getbytevalue(space, w_value):
    value = space.getindex_w(w_value, None)
    if not 0 <= value < 256:
        # this includes the OverflowError in case the long is too large
        raise OperationError(space.w_ValueError, space.wrap(
            "byte must be in range(0, 256)"))
    return chr(value)

def newbytesdata_w(space, w_source, encoding, errors):
    # None value
    if w_source is None:
        if encoding is not None or errors is not None:
            raise OperationError(space.w_TypeError, space.wrap(
                    "encoding or errors without string argument"))
        return []
    # Is it an int?
    try:
        count = space.int_w(w_source)
    except OperationError, e:
        if not e.match(space, space.w_TypeError):
            raise
    else:
        if count < 0:
            raise OperationError(space.w_ValueError,
                                 space.wrap("negative count"))
        if encoding is not None or errors is not None:
            raise OperationError(space.w_TypeError, space.wrap(
                    "encoding or errors without string argument"))
        return ['\0'] * count
    # Unicode with encoding
    if space.isinstance_w(w_source, space.w_unicode):
        if encoding is None:
            raise OperationError(space.w_TypeError, space.wrap(
                    "string argument without an encoding"))
        from pypy.objspace.std.unicodetype import encode_object
        w_source = encode_object(space, w_source, encoding, errors)
        # and continue with the encoded string

    return makebytesdata_w(space, w_source)

def makebytesdata_w(space, w_source):
    w_bytes_method = space.lookup(w_source, "__bytes__")
    if w_bytes_method is not None:
        w_bytes = space.get_and_call_function(w_bytes_method, w_source)
        if not space.isinstance_w(w_bytes, space.w_bytes):
            msg = "__bytes__ returned non-bytes (type '%T')"
            raise operationerrfmt(space.w_TypeError, msg, w_bytes)
        return [c for c in space.bytes_w(w_bytes)]

    # String-like argument
    try:
        string = space.bufferstr_new_w(w_source)
    except OperationError, e:
        if not e.match(space, space.w_TypeError):
            raise
    else:
        return [c for c in string]

    if space.isinstance_w(w_source, space.w_unicode):
        raise OperationError(
            space.w_TypeError,
            space.wrap("cannot convert unicode object to bytes"))

    # sequence of bytes
    w_iter = space.iter(w_source)
    length_hint = space.length_hint(w_source, 0)
    data = newlist_hint(length_hint)
    extended = 0
    while True:
        try:
            w_item = space.next(w_iter)
        except OperationError, e:
            if not e.match(space, space.w_StopIteration):
                raise
            break
        value = getbytevalue(space, w_item)
        data.append(value)
        extended += 1
    if extended < length_hint:
        resizelist_hint(data, extended)
    return data

@unwrap_spec(encoding='str_or_None', errors='str_or_None')
def descr__new__(space, w_stringtype, w_source=None, encoding=None,
                 errors=None):
    from pypy.objspace.std.stringobject import W_StringObject
    if (w_source and space.is_w(space.type(w_source), space.w_bytes) and
        space.is_w(w_stringtype, space.w_bytes)):
        return w_source
    value = ''.join(newbytesdata_w(space, w_source, encoding, errors))
    w_obj = space.allocate_instance(W_StringObject, w_stringtype)
    W_StringObject.__init__(w_obj, value)
    return w_obj

def descr_fromhex(space, w_type, w_hexstring):
    "bytes.fromhex(string) -> bytes\n"
    "\n"
    "Create a bytes object from a string of hexadecimal numbers.\n"
    "Spaces between two numbers are accepted.\n"
    "Example: bytes.fromhex('B9 01EF') -> bytes(b'\\xb9\\x01\\xef')."
    from pypy.objspace.std.bytearraytype import _hexstring_to_array
    from pypy.objspace.std.stringobject import W_StringObject
    if not space.is_w(space.type(w_hexstring), space.w_unicode):
        raise OperationError(space.w_TypeError, space.wrap(
                "must be str, not %s" % space.type(w_hexstring).name))
    hexstring = space.unicode_w(w_hexstring)
    chars = ''.join(_hexstring_to_array(space, hexstring))
    w_obj = space.allocate_instance(W_StringObject, w_type)
    W_StringObject.__init__(w_obj, chars)
    return w_obj

def descr_maketrans(space, w_type, w_from, w_to):
    """bytes.maketrans(frm, to) -> translation table
    
    Return a translation table (a bytes object of length 256) suitable
    for use in the bytes or bytearray translate method where each byte
    in frm is mapped to the byte at the same position in to.
    The bytes objects frm and to must be of the same length."""
    base_table = [chr(i) for i in range(256)]
    list_from = makebytesdata_w(space, w_from)
    list_to = makebytesdata_w(space, w_to)
    
    if len(list_from) != len(list_to):
        raise OperationError(space.w_ValueError, space.wrap(
                "maketrans arguments must have same length"))
    
    for i in range(len(list_from)):
        pos_from = ord(list_from[i])
        char_to = list_to[i]
        base_table[pos_from] = char_to
    
    return wrapstr(space, ''.join(base_table))

# ____________________________________________________________

str_typedef = StdTypeDef("bytes",
    __new__ = interp2app(descr__new__),
    __doc__ = 'bytes(iterable_of_ints) -> bytes\n'
              'bytes(string, encoding[, errors]) -> bytes\n'
              'bytes(bytes_or_buffer) -> immutable copy of bytes_or_buffer\n'
              'bytes(memory_view) -> bytes\n\n'
              'Construct an immutable array of bytes from:\n'
              '    - an iterable yielding integers in range(256)\n'
              '    - a text string encoded using the specified encoding\n'
              '    - a bytes or a buffer object\n'
              '    - any object implementing the buffer API.',
    fromhex = interp2app(descr_fromhex, as_classmethod=True),
    maketrans = interp2app(descr_maketrans, as_classmethod=True),
    )

str_typedef.registermethods(globals())

