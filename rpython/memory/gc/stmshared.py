from rpython.rtyper.lltypesystem import lltype, llmemory, llarena, rffi
from rpython.rlib.rarithmetic import LONG_BIT
from rpython.rlib.objectmodel import free_non_gc_object, we_are_translated
from rpython.rlib.debug import ll_assert, fatalerror
from rpython.rlib import rthread

WORD = LONG_BIT // 8
NULL = llmemory.NULL
WORD_POWER_2 = {32: 2, 64: 3}[LONG_BIT]
assert 1 << WORD_POWER_2 == WORD

# Linux's glibc is good at 'malloc(1023*WORD)': the blocks ("pages") it
# returns are exactly 1024 words apart, reserving only one extra word
# for its internal data
TRANSLATED_PAGE_SIZE = 1023 * WORD

# This is the largest size that StmGCSharedArea will map to its internal
# "pages" structures.
TRANSLATED_SMALL_REQUEST_THRESHOLD = 35 * WORD

# ------------------------------------------------------------
# The basic idea here is that each page will contain objects that are
# each of the same size.  Moreover each page belongs to one thread only:
# only this thread can use it to satisfy more allocations --- with however
# one exception: pages with low usage after a major collection are moved
# to a global list where any thread can pick them up.

PAGE_PTR = lltype.Ptr(lltype.ForwardReference())
PAGE_HEADER = lltype.Struct('PageHeader',
    # -- The following pointer makes a chained list of pages.
    ('nextpage', PAGE_PTR),
    # -- XXX
    ('xxx1', lltype.Signed),
    ('xxx2', llmemory.Address),
    # -- The structure above is 3 words, which is a good value:
    #    '(1023-3) % N' is zero or very small for various small N's,
    #    i.e. there is not much wasted space.
    )
PAGE_PTR.TO.become(PAGE_HEADER)
PAGE_NULL = lltype.nullptr(PAGE_HEADER)

# ------------------------------------------------------------


class StmGCSharedArea(object):
    _alloc_flavor_ = 'raw'

    def __init__(self, gc, page_size, small_request_threshold):
        self.gc = gc
        self.page_size = page_size
        self.small_request_threshold = small_request_threshold
        #
        # This array contains 'length' chained lists of pages.
        # For each size N between WORD and 'small_request_threshold'
        # (included), the corresponding chained list contains pages
        # which store objects of size N.  This is only used for pages
        # with low usage after a major collection; as soon as a page
        # is used, or if its usage says high after a major collection,
        # it belongs to the lists of StmGCThreadLocalAllocator.
        length = small_request_threshold / WORD + 1
        self.low_usage_page = lltype.malloc(rffi.CArray(PAGE_PTR), length,
                                            flavor='raw', zero=True,
                                            immortal=True)
        self.nblocks_for_size = lltype.malloc(rffi.CArray(lltype.Signed),
                                              length, flavor='raw',
                                              immortal=True)
        self.hdrsize = llmemory.raw_malloc_usage(llmemory.sizeof(PAGE_HEADER))
        self.nblocks_for_size[0] = 0    # unused
        for i in range(1, length):
            self.nblocks_for_size[i] = (page_size - self.hdrsize) // (WORD * i)
        assert self.nblocks_for_size[length-1] >= 1

    def setup(self):
        self.ll_low_usage_lock = rthread.allocate_ll_lock()


# ------------------------------------------------------------


class StmGCThreadLocalAllocator(object):
    """A thread-local allocator for the shared area.
    This is an optimization only: it lets us use thread-local variables
    to keep track of what we allocated.
    """
    _alloc_flavor_ = 'raw'

    def __init__(self, sharedarea):
        self.gc = sharedarea.gc
        self.sharedarea = sharedarea
        self.chained_list = NULL
        #
        # The array 'pages_for_size' contains 'length' chained lists
        # of pages currently managed by this thread.
        # For each size N between WORD and 'small_request_threshold'
        # (included), the corresponding chained list contains pages
        # which store objects of size N.
        length = sharedarea.small_request_threshold / WORD + 1
        self.pages_for_size = lltype.malloc(
            rffi.CArray(PAGE_PTR), length, flavor='raw', zero=True)
        #
        # This array contains 'length' chained lists of free locations.
        self.free_loc_for_size = lltype.malloc(
            rffi.CArray(llmemory.Address), length, flavor='raw', zero=True)
        #
        if not we_are_translated():
            self._seen_pages = set()

    def _malloc_size_class(self, size_class):
        """Malloc one object of the given size_class (== number of WORDs)."""
        ll_assert(size_class > 0, "malloc_size_class: null or neg size_class")
        ll_assert(size_class <= self.sharedarea.small_request_threshold,
                  "malloc_size_class: too big")
        #
        # The result is simply 'free_loc_for_size[size_class]'
        result = self.free_loc_for_size[size_class]
        if not result:
            result = self._allocate_new_page(size_class)
        self.free_loc_for_size[size_class] = result.address[0]
        llarena.arena_reset(result, llmemory.sizeof(llmemory.Address), 0)
        return result
    _malloc_size_class._always_inline_ = True

    def _free_size_class(self, adr, size_class):
        """Free a single location 'adr', which is of the given size_class."""
        # just link 'adr' to the start of 'free_loc_for_size[size_class]'
        adr = llarena.getfakearenaaddress(adr)
        llarena.arena_reset(adr, size_class << WORD_POWER_2, 0)
        llarena.arena_reserve(adr, llmemory.sizeof(llmemory.Address))
        adr.address[0] = self.free_loc_for_size[size_class]
        self.free_loc_for_size[size_class] = adr
    _free_size_class._always_inline_ = True

    def _allocate_new_page(self, size_class):
        """Allocate and return a new page for the given size_class."""
        #
        result = llarena.arena_malloc(self.sharedarea.page_size, 0)
        if not result:
            fatalerror("FIXME: Out of memory! (should raise MemoryError)")
            return NULL
        if not we_are_translated():
            self._seen_pages.add(result)
        llarena.arena_reserve(result, llmemory.sizeof(PAGE_HEADER))
        #
        # Initialize the fields of the resulting page
        page = llmemory.cast_adr_to_ptr(result, PAGE_PTR)
        page.nextpage = self.pages_for_size[size_class]
        self.pages_for_size[size_class] = page
        #
        # Initialize the chained list in the page
        head = result + llmemory.sizeof(PAGE_HEADER)
        ll_assert(not self.free_loc_for_size[size_class],
                  "free_loc_for_size is supposed to contain NULL here")
        self.free_loc_for_size[size_class] = head
        #
        i = self.sharedarea.nblocks_for_size[size_class]
        nsize = size_class << WORD_POWER_2
        current = head
        while True:
            llarena.arena_reserve(current, llmemory.sizeof(llmemory.Address))
            i -= 1
            if i == 0:
                break
            next = current + nsize
            current.address[0] = next
            current = next
        current.address[0] = llmemory.NULL
        #
        return head


    def malloc_object(self, totalsize):
        """Malloc.  You should also call add_regular() later, or keep it in
        some other data structure.  Note that it is not zero-filled."""
        nsize = llmemory.raw_malloc_usage(totalsize)
        if nsize <= self.sharedarea.small_request_threshold:
            size_class = (nsize + WORD_POWER_2 - 1) >> WORD_POWER_2
            result = self._malloc_size_class(size_class)
        else:
            result = llarena.arena_malloc(
                llmemory.raw_malloc_usage(totalsize), 0)
        llarena.arena_reserve(result, _dummy_size(totalsize))
        return result + self.gc.gcheaderbuilder.size_gc_header

    def add_regular(self, obj):
        """After malloc_object(), register the object in the internal chained
        list.  For objects whose 'revision' field is not otherwise needed."""
        self.gc.set_obj_revision(obj, self.chained_list)
        self.chained_list = obj

    def free_object(self, obj):
        adr1 = obj - self.gc.gcheaderbuilder.size_gc_header
        osize = self.gc.get_size_incl_hash(obj)
        if osize <= self.sharedarea.small_request_threshold:
            size_class = (osize + WORD_POWER_2 - 1) >> WORD_POWER_2
            self._free_size_class(adr1, size_class)
        else:
            llarena.arena_free(llarena.getfakearenaaddress(adr1))

    def free_and_clear(self):
        obj = self.chained_list
        self.chained_list = NULL
        while obj:
            next = self.gc.obj_revision(obj)
            self.free_object(obj)
            obj = next

    def free_and_clear_list(self, lst):
        while lst.non_empty():
            self.free_object(lst.pop())

    def delete(self):
        lltype.free(self.free_loc_for_size, flavor='raw')
        lltype.free(self.pages_for_size, flavor='raw')
        free_non_gc_object(self)


# ____________________________________________________________

def _dummy_size(size):
    if we_are_translated():
        return size
    if isinstance(size, int):
        size = llmemory.sizeof(lltype.Char) * size
    return size
