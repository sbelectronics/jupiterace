from __future__ import print_function
import string
import sys
import time
from optparse import OptionParser
#from hexfile import HexFile

from supervisor_direct import SupervisorDirect

def hex_escape(s):
    printable = string.ascii_letters + string.digits + string.punctuation + ' '
    return ''.join(c if c in printable else r'\x{0:02x}'.format(ord(c)) for c in s)

def load_image(super, addr, fn):
    filebytes = open(fn, "rb").read()
    super.mem_write_start(addr)    
    try:
        for b in filebytes:
            super.mem_write_fast(addr, b)
            addr += 1
    finally:
        super.mem_write_end()   

def save_image(super, addr, size, fn):
    super.mem_read_start(addr)    
    try:
        f = open(fn, "wb")
        for i in range(0, size):
            byte = super.mem_read_fast(addr)
            f.write(byte.to_bytes(1,"big"))
            addr+=1
    finally:
        super.mem_read_end()

def verify_image(super, addr, size, fn):
    filebytes = open(fn, "rb").read()
    if (size==0) or (size is None):
        size = len(filebytes)

    super.mem_read_start(addr)
    try:
        for i in range(0, size):
            byte = super.mem_read_fast(addr)
            if byte != filebytes[i]:
                print("Mismatch Addr=%04X Mem=%02X File=%02X" % (addr, byte, filebytes[i]))
            addr+=1
    finally:
        super.mem_read_end()

def fill(super, addr, size, value):
    super.mem_write_start(addr)    
    try:
        for i in range(0, size):
            super.mem_write_fast(addr, value)
            addr+=1
    finally:
        super.mem_write_end()

def screendump(super):
    addr = 0x2000;
    for i in range(0,768):
        b = super.mem_read(addr)
        print(chr(b),end="")
        if (i+1)%32 == 0:
            print()
        addr+=1
    print()

def pushline(super, line):
    time.sleep(0.001)

    ready = False
    while not ready:
        try:
            super.take_bus()
            # just checking 3C28 is probably sufficient...
            ready = ((super.mem_read(0x3C28) & 0x20) == 0) and (super.mem_read_word(0x3C20)==0x26E1) and (super.mem_read_word(0x3C22)==0x26E2)
        finally:
            super.release_bus(reset=True)

    time.sleep(0.001)

    try:
        super.take_bus()
        bufstart = super.mem_read(0x3C24) + (super.mem_read(0x3C25)<<8)  - 0x400

        buf = bufstart

        super.mem_write(buf,0)
        buf += 1

        for k in line:
            super.mem_write(buf,ord(k))
            buf += 1

        super.mem_write(buf,0)

        super.mem_write_word(0x3C20, bufstart+len(line)+1)  # end of current logical line
        super.mem_write_word(0x3C22, bufstart+len(line)+2)

        super.mem_write(0x3c28, 0x21)
    finally:
        super.release_bus(reset=True)


def pushfile(super, fn):
    lines = open(fn).readlines()
    for line in lines:
        line = line.strip()
        pushline(super, line)
        #time.sleep(1)


# with ABC in the buffer
#   3C1E = 26E0
#   3C20 = 26E4
#   3C22 = 26E5
#   3C24 = 26E0
#   3C26 = 0
#   3C27 = 0
#   3C28 = 1
#   3C29 = 0
#   3C2A = 0
#
#   26E0 = 00
#   26E1 = 61
#   26E2 = 62
#   26E3 = 63
#   26E4 = 97  ;; this might be 0 sometimes
#   26E5 = 20
#

def pushkeys(super):
    startbuf = super.mem_read(0x3C24) + (super.mem_read(0x3C25)<<8)  - 0x400
    print("startbuf=%x" % startbuf)

    super.mem_write(startbuf,0)
    super.mem_write(startbuf+1,ord('a'))
    super.mem_write(startbuf+2,ord('b'))
    super.mem_write(startbuf+3,ord('c'))
    super.mem_write(startbuf+4,0x97)

    super.mem_write_word(0x3C1E, 0x26E0)
    super.mem_write_word(0x3C20, 0x26E4)
    super.mem_write_word(0x3C22, 0x26E5)
    super.mem_write_word(0x3C24, 0x26E0)


    """
    super.mem_write(startbuf+1,ord(' '))
    super.mem_write(startbuf+2,ord('1'))
    super.mem_write(startbuf+3,ord(' '))
    super.mem_write(startbuf+4,ord('.'))
    super.mem_write(startbuf+5,ord(' '))
    super.mem_write(startbuf+6,ord('2'))
    super.mem_write(startbuf+7,ord(' '))
    super.mem_write(startbuf+8,ord('.'))
    super.mem_write(startbuf+9,ord(' '))
    super.mem_write(startbuf+10,ord('3'))
    super.mem_write(startbuf+11,ord(' '))
    super.mem_write(startbuf+12,ord('.'))
    super.mem_write(startbuf+13,ord(' '))
    super.mem_write(startbuf+14,ord('4'))
    super.mem_write(startbuf+15,ord(' '))
    super.mem_write(startbuf+16,ord('.'))
    super.mem_write(startbuf+17,0)
    """

    #super.mem_write_word(0x3C22, startbuf+17)

    # set statin bit 5 to signal enter has been pushed
    statin = super.mem_read(0x3c28)
    statin = statin | 0x20
    print("statin=%x" % statin)
    #super.mem_write(0x3c28, statin)

    #super.mem_write(0x3C22, startbuf+6)

def clearkeys(super):
    startbuf = super.mem_read(0x3C24) + (super.mem_read(0x3C25)<<8) + 2 - 0x400
    print("startbuf=%x" % startbuf)

    super.mem_write(startbuf,ord('x'))
    super.mem_write(startbuf+1,ord('x'))
    super.mem_write(startbuf+2,ord('x'))
    super.mem_write(startbuf+3,ord('x'))
    super.mem_write(startbuf+4,ord('x'))
    super.mem_write(startbuf+5,ord('x'))
    super.mem_write(startbuf+6,ord('x'))
    super.mem_write(startbuf+7,ord('x'))
    super.mem_write(startbuf+8,ord('x'))
    super.mem_write(startbuf+9,ord('x'))
    super.mem_write(startbuf+10,ord('x'))
    super.mem_write(startbuf+11,ord('x'))
    super.mem_write(startbuf+12,ord('x'))
    super.mem_write(startbuf+13,0)

def patch(buf, pat, replace):
    for i in range(0, len(buf)):
        if i+len(pat)>=len(buf):
            return
        match = True;
        for j in range(0,len(pat)):
            if buf[i+j]!=pat[j]:
                match = False
        if match:
            print("patch at %X" % i)
            for j in range(0,len(pat)):
                buf[i+j] = replace[j]

def loadtap(super, fn, patchudg):
    b = open(fn,"rb").read()

    headerLen = b[0] | b[1]<<8
    if (headerLen!=26):
        printf("Invalid header len: %d" % headerLen);
        sys.exit(-1)

    fType = b[2];
    fLen = b[13] | b[14]<<8
    startAddr = b[15] | b[16]<<8
    curWord = b[17] | b[18]<<8
    current = b[19] | b[20]<<8
    context = b[21] | b[22]<<8
    voclnk = b[23] | b[24]<<8
    stkbot = b[25] | b[26]<<8

    print("ftype: %X" % fType)
    print("flen: %X" % fLen)
    print("startAddr: %X" % startAddr)
    print("curWord: %X" % curWord)
    print("current: %X" % current)
    print("context: %X" % context)
    print("voclnk: %X" % voclnk)
    print("stkbot: %X" % stkbot)

    addr = startAddr
    offset = 28
    while (offset<=len(b)):
        blkLen = b[offset] | b[offset+1]<<8
        offset += 2
        print("blklen: %X" % blkLen)

        blk = bytearray(b[offset:(offset+blkLen)])
        if patchudg:
            # modify loaded code to use the version of the font table that does not wait for
            # video blank. This fixes a memory corruption issue on my homebuilt ACE.
            patch(blk, bytes([0x11,0x10,0xff,0x2b,0xd2,0x0d]), bytes([0x11,0x10,0xff,0x27,0xd2,0x0d]))
            patch(blk, bytes([0x11,0x10,0x00,0x2c,0xd2,0x0d]), bytes([0x11,0x10,0x00,0x28,0xd2,0x0d]))

        super.mem_write_start(addr)
        for i in range(0, blkLen):
            if i<len(blk):
                super.mem_write_fast(addr+i, blk[i])
        super.mem_write_end()

        offset+=blkLen+1
        addr += blkLen

    super.mem_write_word(0x3C31, current)
    super.mem_write_word(0x3C33, context)
    super.mem_write_word(0x3C35, voclnk)
    super.mem_write_word(0x3C37, stkbot)

    super.mem_write_word(current, curWord)

def process_ace(src):
    # decompress a .ace file
    dest = bytearray()
    i = 0
    while (i<len(src)):
        if src[i] == 0xED:
            i+=1
            count = src[i]
            if count == 0x00:
                return dest
            i+=1
            val = src[i]
            for j in range(0,count):
                dest.append(val)
        else:
            dest.append(src[i])
        i+=1
    return dest

def loadace(super, fn, patchudg):
    b = open(fn,"rb").read()
    b = process_ace(b)
    if patchudg:
        # modify loaded code to use the version of the font table that does not wait for
        # video blank. This fixes a memory corruption issue on my homebuilt ACE.
        patch(b, bytes([0x11,0x10,0xff,0x2b,0xd2,0x0d]), bytes([0x11,0x10,0xff,0x27,0xd2,0x0d]))
        patch(b, bytes([0x11,0x10,0x00,0x2c,0xd2,0x0d]), bytes([0x11,0x10,0x00,0x28,0xd2,0x0d]))
    addr = 0x2000
    super.mem_write_start(addr)
    for v in b:
        if (addr>=0x2400) and (addr<=0x27FF):
            super.mem_write_fast(addr-0x400, v)
        elif (addr>=0x2C00) and (addr<=0x2FFF):
            super.mem_write_fast(addr-0x400, v)
        else:
            super.mem_write_fast(addr,v)
        addr += 1
    super.mem_write_end()

    print("loaded %d bytes" % len(b))

def main():
    parser = OptionParser(usage="supervisor [options] command",
            description="Commands: ...")

    parser.add_option("-A", "--addr", dest="addr",
         help="address", metavar="ADDR", type="string", default=0)
    parser.add_option("-C", "--count", dest="count",
         help="count", metavar="ADDR", type="string", default="65536")
    parser.add_option("-V", "--value", dest="value",
         help="value", metavar="VAL", type="string", default=0)
    parser.add_option("-P", "--ascii", dest="ascii",
         help="print ascii value", action="store_true", default=False)
    parser.add_option("-O", "--octal", dest="octal",
         help="print octal value", action="store_true", default=False)         
    parser.add_option("-R", "--rate", dest="rate",
         help="rate for slow clock", metavar="HERTZ", type="int", default=10)
    parser.add_option("-v", "--verbose", dest="verbose",
         help="verbose", action="store_true", default=False)
    parser.add_option("-f", "--filename", dest="filename",
         help="filename", default=None)
    parser.add_option("-r", "--reset", dest="reset_on_release",
         help="reset on release of bus", action="store_true", default=False)
    parser.add_option("-n", "--norelease", dest="norelease",
         help="do not release bus", action="store_true", default=False)
    parser.add_option("-i", "--indirect", dest="direct",
         help="use the python supervisor", action="store_false", default=True)
    parser.add_option("-D", "--delaymult", dest="delay_mult",
         help="multiplier for delay", type="int", default=None)
    parser.add_option("-S", "--SVAL", dest="stringval",
         help="stringvalue", default=None, type="string")
    parser.add_option("-U", "--patchudg", dest="patchudg",
         help="patch udg", action="store_true", default=False)

    #parser.disable_interspersed_args()

    (options, args) = parser.parse_args(sys.argv[1:])

    if len(args)==0:
        print("missing command")
        sys.exit(-1)

    cmd = args[0]
    args=args[1:]

    if options.direct:
      super = SupervisorDirect(options.verbose)
    else:
      raise "Unsupported"

    if options.delay_mult:
        super.delay_mult(options.delay_mult)
    
    addr = None
    if (options.addr):
        if options.addr.startswith("0x") or options.addr.startswith("0X"):
            addr = int(options.addr[2:], 16)
        elif options.addr.startswith("$"):
            addr = int(options.addr[1:], 16)
        elif options.addr.lower().endswith("q") or options.addr.lower().endswith("a"):
            addr = int(options.addr[:-4], 8) << 8 | int(options.addr[-4:-1], 8)
        elif options.octal:
            addr = int(options.addr[:-3], 8) << 8 | int(options.addr[-3:], 8)
        else:
            addr = int(options.addr)

    value = None
    if (options.value):
        if options.value.startswith("0x") or options.value.startswith("0X"):
            value = int(options.value[2:], 16)
        elif options.addr.startswith("$"):
            value = int(options.value[1:], 16)
        elif options.value.lower().endswith("q"):
            value = int(options.value[:-1], 8)
        elif options.octal:
            value = int(options.value, 8)
        else:
            value = int(options.value)

    count = None
    if (options.count):
        if options.count.startswith("0x") or options.count.startswith("0X"):
            count = int(options.count[2:], 16)
        elif options.count.startswith("$"):
            count = int(options.count[1:], 16)
        elif options.count.lower().endswith("q") or options.count.lower().endswith("a"):
            count = int(options.count[:-4], 8) << 8 | int(options.count[-4:-1], 8)
        #elif options.octal:  don't assume octal applies to counts
        #    addr = int(options.addr[:-3], 8) << 8 | int(options.addr[-3:], 8)
        else:
            count = int(options.count)

    if (cmd=="pushkeys"):
        try:
            super.take_bus()
            pushkeys(super)
        finally:
            if not options.norelease:
                super.release_bus(reset=True) 

    elif (cmd=="clearkeys"):
        try:
            super.take_bus()
            clearkeys(super)
        finally:
            if not options.norelease:
                super.release_bus(reset=True)

    elif (cmd=="screendump"):
        try:
            super.take_bus()
            screendump(super)
        finally:
            if not options.norelease:
                super.release_bus(reset=True)

    elif (cmd=="loadtap"):
        try:
            super.take_bus()
            loadtap(super, options.filename, options.patchudg)
        finally:
            if not options.norelease:
                super.release_bus(reset=True)

    elif (cmd=="loadace"):
        try:
            super.take_bus()
            loadace(super, options.filename, options.patchudg)
        finally:
            if not options.norelease:
                super.release_bus(reset=True)                 

    elif (cmd=="pushfile"):
        pushfile(super, options.filename)

    elif (cmd=="pushline"):
        pushline(super, options.stringval)

    elif (cmd=="reset"):
        try:
            super.take_bus()
        finally:
            if not options.norelease:
                super.release_bus(reset=True)

    elif (cmd=="memdump"):
        try:
            super.take_bus()
            for i in range(addr, addr+count):
                val = super.mem_read(i)
                if options.octal:
                    if options.ascii:
                        print("%03o%03o %03o %s" % (i>>8, i&0xFF, val, hex_escape(chr(val))))
                    else:
                        print("%03o%03o %03o" % (i>>8, i&0xFF, val))
                else:
                    if options.ascii:
                        print("%04X %02X %s" % (i, val, hex_escape(chr(val))))
                    else:
                        print("%04X %02X" % (i, val))
        finally:
            if not options.norelease:
                super.release_bus()

    elif (cmd=="peek"):
        try:
            super.take_bus()
            if options.octal:
                print("%03o" % super.mem_read(addr))
            else:
                print("%02X" % super.mem_read(addr))

        finally:
            if not options.norelease:
                super.release_bus()

    elif (cmd=="poke"):
        try:
            super.take_bus()
            super.mem_write(addr, value)
        finally:
            if not options.norelease:
                super.release_bus()

    elif (cmd=="inp"):
        try:
            super.take_bus()
            if options.octal:
                print("%03o" % super.port_read(addr))
            else:
                print("%02X" % super.port_read(addr))

        finally:
            if not options.norelease:
                super.release_bus()

    elif (cmd=="out"):
        try:
            super.take_bus()
            super.port_write(addr, value)
        finally:
            if not options.norelease:
                super.release_bus()

    elif (cmd=="showint"):
        last=None
        while True:
            v = ((super.ixData.get_gpio(1)&INT) !=0)
            if v!=last:
                print(v)
                last=v

    elif (cmd=="loadimg"):
        try:
            super.take_bus()
            load_image(super, addr, options.filename)
        finally:
            if not options.norelease:
                super.release_bus()

    elif (cmd=="verifyimg"):
        try:
            super.take_bus()
            verify_image(super, addr, count, options.filename)
        finally:
            if not options.norelease:
                super.release_bus()                

    elif (cmd=="loadh8t"):
        try:
            super.take_bus()
            load_h8t(super, options.filename)
        finally:
            if not options.norelease:
                super.release_bus()

    elif (cmd=="loadh8d"):
        try:
            super.take_bus()
            load_h8d(super, options.filename)
        finally:
            if not options.norelease:
                super.release_bus()

    elif (cmd=="saveimg"):
        try:
            super.take_bus()
            save_image(super, addr, count, options.filename)
            super.reset()
        finally:
            if not options.norelease:
                super.release_bus()

    elif (cmd=="fill"):
        try:
            super.take_bus()
            fill(super, addr, count, value)
        finally:
            if not options.norelease:
                super.release_bus()

    elif (cmd=="watch"):
        lastVal = -1
        count = 0
        while True:
            try:
                super.take_bus()
                val = super.mem_read(addr)
                if (val != lastVal):
                    if options.octal:
                        print("%03o" % val)
                    else:
                        print("0x%X" % val)
                    lastVal = val
            finally:
                if not options.norelease:
                    super.release_bus()
            time.sleep(0.1)
            count = count + 1
            if (count % 100) == 0:
                print("count: %d" % count)

    elif (cmd=="watchinp"):
        lastVal = -1
        count = 0
        while True:
            try:
                super.take_bus()
                val = super.port_read(addr)
                if (val != lastVal):
                    print("0x%X" % val)
                    lastVal = val
            finally:
                if not options.norelease:
                    super.release_bus()
            time.sleep(0.1)
            count = count + 1
            if (count % 100) == 0:
                print("count: %d" % count)

    else:
        print("Unknown command: %s" % cmd)


if __name__=="__main__":
    main()
