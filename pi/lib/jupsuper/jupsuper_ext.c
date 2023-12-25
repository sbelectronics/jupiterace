#include <Python.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/ioctl.h>
#include <pigpio.h>

// mcp23017 registers
#define IODIR  0x00
#define IPOL  0x02
#define GPINTEN  0x04
#define DEFVAL  0x06
#define INTCON  0x08
#define IOCON  0x0A
#define GPPU  0x0C
#define INTF  0x0E
#define MCP23017_GPIO  0x12
#define OLAT  0x14

#define PIN_D0 4
#define PIN_D1 5
#define PIN_D2 6
#define PIN_D3 7
#define PIN_D4 8
#define PIN_D5 9
#define PIN_D6 10
#define PIN_D7 11

#define PIN_A0 16
#define PIN_A1 17
#define PIN_A2 18
#define PIN_A3 19
#define PIN_A4 20
#define PIN_A5 21
#define PIN_A6 22
#define PIN_A7 23

#define PIN_BUSEN 26
#define PIN_BUSDIR 27
#define PIN_MREQ 14
#define PIN_IOREQ 15
#define PIN_RD 3
#define PIN_WR 2

#define PIN_BUSRQ 12
#define PIN_BUSAK 13

#define PIN_ADDR_L 24
#define PIN_ADDR_H 25

#define DATADIR_READ 0
#define DATADIR_WRITE 1

static int datapins[] = {PIN_D0, PIN_D1, PIN_D2, PIN_D3,
                         PIN_D4, PIN_D5, PIN_D6, PIN_D7};

static int addrpins[] = {PIN_A0, PIN_A1, PIN_A2, PIN_A3,
                         PIN_A4, PIN_A5, PIN_A6, PIN_A7};

uint16_t isTaken;
uint16_t delayMult;
uint16_t lastHiAddr;
uint16_t lastHiAddrSet;

void short_delay(void)
{
    // Just do nothing for a while. This is to allow the RAM some time to do it's work.
    //
    int j;

    for (j=0; j<50; j++) {
        asm("nop");
    }
}

void medium_delay(void)
{
    // Just do nothing for a while. This is to allow the RAM some time to do it's work.
    //
    int j;
    int dv = 200 * delayMult;

    for (j=0; j<dv; j++) {
        asm("nop");
    }
}

static void _databus_config_read()
{
  for (int i=0; i<8; i++) {
    gpioSetMode(datapins[i], PI_INPUT);
  }
  gpioWrite(PIN_BUSDIR, DATADIR_READ);
}

static void _databus_config_write()
{
  gpioWrite(PIN_BUSDIR, DATADIR_WRITE);
  for (int i=0; i<8; i++) {
    gpioSetMode(datapins[i], PI_OUTPUT);
  }
}

static uint16_t _data_read()
{
  uint32_t data = gpioRead_Bits_0_31();
  return (((data >> 4)) & 0xFF);
}

static void _data_write(uint16_t val)
{
  uint32_t data = ((val) & 0xFF) << 4;

  gpioWrite_Bits_0_31_Clear(0x00000FF0);
  gpioWrite_Bits_0_31_Set(data);
}

static void _addr_lo_write(uint16_t val)
{
  uint32_t data = ((val) & 0xFF) << 16;

  gpioWrite(PIN_ADDR_H, 0); /* latch the high bits */

  gpioWrite_Bits_0_31_Clear(0x00FF0000);
  gpioWrite_Bits_0_31_Set(data);

  gpioWrite(PIN_ADDR_L, 1); /* make lo latch transparent */
}

static void _addr_hi_write(uint16_t val)
{
  uint32_t data = ((val) & 0xFF) << 16;

  gpioWrite(PIN_ADDR_L, 0); /* latch the low bits */

  gpioWrite_Bits_0_31_Clear(0x00FF0000);
  gpioWrite_Bits_0_31_Set(data);

  gpioWrite(PIN_ADDR_H, 1); /* make the high latch transparent */
}

static void _set_address(uint32_t addr)
{
  uint8_t hiAddr;

  // Note: Inverted
  hiAddr = (addr>>8) & 0xFF;                                            // A8..A15.
  if ((hiAddr != lastHiAddr) || (!lastHiAddrSet)) {
    _addr_hi_write(hiAddr);
    lastHiAddr = hiAddr;
    lastHiAddrSet = 1;
  }

  _addr_lo_write(addr & 0xFF);
}

static void _mrDown()
{
  gpioWrite(PIN_MREQ, 0);
  gpioWrite(PIN_RD, 0);
}

static void _mrUp()
{
  gpioWrite(PIN_RD, 1);
  gpioWrite(PIN_MREQ, 1);
}

static void _mwDown()
{
  gpioWrite(PIN_MREQ, 0);
  gpioWrite(PIN_WR, 0);
}

static void _mwUp()
{
  gpioWrite(PIN_WR, 1);
  gpioWrite(PIN_MREQ, 1);
}

static void _iorDown()
{
  gpioWrite(PIN_IOREQ, 0);
  gpioWrite(PIN_RD, 0);
}

static void _iorUp()
{
  gpioWrite(PIN_RD, 1);
  gpioWrite(PIN_IOREQ, 1);
}

static void _iowDown()
{
  gpioWrite(PIN_IOREQ, 0);
  gpioWrite(PIN_WR, 0);
}

static void _iowUp()
{
  gpioWrite(PIN_WR, 1);
  gpioWrite(PIN_IOREQ, 1);
}

static void _release_bus(uint8_t reset)
{
  if (isTaken<=0) {
    printf("WARNING: _release_bus while isTaken==%d\n", isTaken);
  }
  isTaken--;

  short_delay();

  gpioWrite(PIN_BUSEN, 1);  /* Release the bus drivers */

  gpioWrite(PIN_BUSRQ, 0);  /* release busrq. It's active high. */

  //self.log("wait for not HLDA");
  while (1) {
    if (gpioRead(PIN_BUSAK)==1) {
      break;
    }
  }
}

static void _take_bus()
{
  if (isTaken>0) {
    printf("WARNING: _take_bus while isTaken==%d\n", isTaken);
  }
  isTaken++;

  short_delay();

  gpioWrite(PIN_BUSRQ, 1);

  //self.log("wait for HLDA");
  while (1) {
    if (gpioRead(PIN_BUSAK)==0) {
      break;
    }
  }

  short_delay();
  _mrUp();
  _mwUp();
  _iorUp();
  _iowUp();

  gpioWrite(PIN_BUSEN, 0); /* Assert the bus drivers */
}

static uint16_t  _port_read(uint32_t addr)
{
  uint16_t result;

  _set_address(addr);
  short_delay();
  _iorDown();
  medium_delay();
  result = _data_read();
  _iorUp();
  return result;
}

static void _port_write(uint32_t addr, uint16_t val)
{
  _set_address(addr);
  _data_write(val);
  short_delay();
  _iowDown();
  medium_delay();
  _iowUp();
  short_delay();
}

static void _mem_read_start(uint32_t addr)
{
  lastHiAddrSet = 0;
}

static void _mem_read_end(void)
{
}

static uint16_t _mem_read_fast(uint32_t addr)
{
  uint16_t result;

  _set_address(addr);
  short_delay();
  _mrDown();
  medium_delay();
  result = _data_read();
  _mrUp();
  return result;
}

static uint16_t _mem_read(uint32_t addr)
{
  uint16_t result;
  _mem_read_start(addr);
  result = _mem_read_fast(addr);
  _mem_read_end();
  return result;
}

static void _mem_write_start(uint32_t addr)
{
  lastHiAddrSet = 0;
  _databus_config_write();
}

static void _mem_write_end()
{
  _databus_config_read();
}

static void _mem_write_fast(uint32_t addr, uint16_t val)
{
  _set_address(addr);
  _data_write(val);
  short_delay();
  _mwDown();
  medium_delay();
  _mwUp();
  short_delay();
}

static void _mem_write(uint32_t addr, uint16_t val)
{
  _mem_write_start(addr);
  _mem_write_fast(addr, val);
  _mem_write_end();
}

static PyObject *jupsuper_init(PyObject *self, PyObject *args)
{
  if (gpioInitialise() < 0) {
    Py_RETURN_FALSE;
  }

  _databus_config_read();                   // configure data buffers for read

  gpioWrite(PIN_BUSRQ, 0);                  // Ensure BUSRQ is released
  gpioSetMode(PIN_BUSRQ, PI_OUTPUT);

  gpioWrite(PIN_BUSDIR, 0);                 // Default BUSDIR to READ
  gpioSetMode(PIN_BUSDIR, PI_OUTPUT);

  gpioWrite(PIN_BUSEN, 1);                  // Ensure BUSEN is released
  gpioSetMode(PIN_BUSEN, PI_OUTPUT);

  gpioSetMode(PIN_ADDR_L, PI_OUTPUT);
  gpioSetMode(PIN_ADDR_H, PI_OUTPUT);

  gpioSetMode(PIN_RD, PI_OUTPUT);
  gpioSetMode(PIN_WR, PI_OUTPUT);
  gpioSetMode(PIN_IOREQ, PI_OUTPUT);
  gpioSetMode(PIN_MREQ, PI_OUTPUT);
  gpioSetMode(PIN_A0, PI_OUTPUT);    
  gpioSetMode(PIN_A1, PI_OUTPUT);  
  gpioSetMode(PIN_A2, PI_OUTPUT);  
  gpioSetMode(PIN_A3, PI_OUTPUT);  
  gpioSetMode(PIN_A4, PI_OUTPUT);  
  gpioSetMode(PIN_A5, PI_OUTPUT);  
  gpioSetMode(PIN_A6, PI_OUTPUT);  
  gpioSetMode(PIN_A7, PI_OUTPUT);  

  _mrUp();
  _mwUp();
  _iorUp();
  _iowUp();

  delayMult = 1;
  isTaken = 1;
  _release_bus(0);

  Py_RETURN_TRUE;
}

static PyObject *jupsuper_release_bus(PyObject *self, PyObject *args)
{
   int reset;    // not "bool x"

   if (!PyArg_ParseTuple(args, "p", &reset)) {
     return NULL;
   }

  _release_bus(reset);

  return Py_BuildValue("");
}

static PyObject *jupsuper_take_bus(PyObject *self, PyObject *args)
{
  _take_bus();

  return Py_BuildValue("");
}

static PyObject *jupsuper_is_taken(PyObject *self, PyObject *args)
{
  if (isTaken>0) {
    Py_RETURN_TRUE;
  } else {
    Py_RETURN_FALSE;
  }
}

// this is probably not faster than just calling mem_snoop from python
static PyObject *jupsuper_wait_signal(PyObject *self, PyObject *args)
{
  uint8_t hit1=0;
  uint8_t hit2=0;
  struct  timespec tStart;
  struct  timespec tNow;
  long elapsed_ms;

  clock_gettime(CLOCK_REALTIME, &tStart);
  while (1) {
    uint16_t m = _data_read();
    if (m == 0x73E7) {
      hit1=1;
    } else if (m == 0xF912) {
      hit2=1;
    }
    if (hit1 && hit2) {
      Py_RETURN_TRUE;  
    }
    clock_gettime(CLOCK_REALTIME, &tNow);
    elapsed_ms = round((tNow.tv_nsec - tStart.tv_nsec)/1.0e6);
    if (elapsed_ms > 100) {
      Py_RETURN_FALSE;
    }
  }
}

static PyObject *jupsuper_port_read(PyObject *self, PyObject *args)
{
  uint32_t addr;
  uint16_t val;

  if (!PyArg_ParseTuple(args, "I", &addr)) {
    return NULL;
  }

  val = _port_read(addr);

  return Py_BuildValue("H", val);
}

static PyObject *jupsuper_port_write(PyObject *self, PyObject *args)
{
  uint32_t addr;
  uint16_t val;

  if (!PyArg_ParseTuple(args, "IH", &addr, &val)) {
    return NULL;
  }

  _port_write(addr, val);

  return Py_BuildValue("");
}

static PyObject *jupsuper_mem_read_start(PyObject *self, PyObject *args)
{
  uint32_t addr;
  if (!PyArg_ParseTuple(args, "I", &addr)) {
    return NULL;
  }

  _mem_read_start(addr);

  return Py_BuildValue("");
}

static PyObject *jupsuper_mem_read_end(PyObject *self, PyObject *args)
{
  _mem_read_end();

  return Py_BuildValue("");
}

static PyObject *jupsuper_mem_read_fast(PyObject *self, PyObject *args)
{
  uint32_t addr;
  uint16_t val;

  if (!PyArg_ParseTuple(args, "I", &addr)) {
    return NULL;
  }

  val = _mem_read_fast(addr);

  return Py_BuildValue("H", val);
}

static PyObject *jupsuper_mem_read(PyObject *self, PyObject *args)
{
  uint32_t addr;
  uint16_t val;

  if (!PyArg_ParseTuple(args, "I", &addr)) {
    return NULL;
  }

  val = _mem_read(addr);

  return Py_BuildValue("H", val);
}

static PyObject *jupsuper_mem_snoop(PyObject *self, PyObject *args)
{
  uint16_t val;

  val = _data_read();

  return Py_BuildValue("H", val);
}

static PyObject *jupsuper_mem_write_start(PyObject *self, PyObject *args)
{
  uint32_t addr;
  if (!PyArg_ParseTuple(args, "I", &addr)) {
    return NULL;
  }

  _mem_write_start(addr);

  return Py_BuildValue("");
}

static PyObject *jupsuper_mem_write_end(PyObject *self, PyObject *args)
{
  _mem_write_end();

  return Py_BuildValue("");
}

static PyObject *jupsuper_mem_write_fast(PyObject *self, PyObject *args)
{
  uint32_t addr;
  uint16_t val;

  if (!PyArg_ParseTuple(args, "IH", &addr, &val)) {
    return NULL;
  }

  _mem_write_fast(addr, val);

  return Py_BuildValue("");
}

static PyObject *jupsuper_mem_write_buffer(PyObject *self, PyObject *args)
{
  uint32_t addr;
  Py_buffer pybuf;
  unsigned char bytes[128];
  int res;

  if (!PyArg_ParseTuple(args, "Iy*", &addr, &pybuf)) {
    return NULL;
  }

  res = PyBuffer_ToContiguous(bytes, &pybuf, 128, 'C');
  if (res!=0) {
    return NULL;
  }

  for (int i=0; i<64; i++) {
    unsigned short w;
    w = (bytes[i*2]<<8) | bytes[i*2+1];
    _mem_write_fast(addr,w);
    addr += 2;
  }

  PyBuffer_Release(&pybuf);

  return Py_BuildValue("");
}

static PyObject *jupsuper_mem_write(PyObject *self, PyObject *args)
{
  uint32_t addr;
  uint16_t val;

  if (!PyArg_ParseTuple(args, "IH", &addr, &val)) {
    return NULL;
  }

  _mem_write(addr, val);

  return Py_BuildValue("");
}

/*
static PyObject *jupsuper_invert_hold(PyObject *self, PyObject *args)
{
  uint16_t val;

  if (!PyArg_ParseTuple(args, "H", &val)) {
    return NULL;
  }

  invertHold = val;

  return Py_BuildValue("");
}
*/

static PyObject *jupsuper_delay_mult(PyObject *self, PyObject *args)
{
  uint16_t val;

  if (!PyArg_ParseTuple(args, "H", &val)) {
    return NULL;
  }

  delayMult = val;

  return Py_BuildValue("");
}

static PyMethodDef jupsuper_methods[] = {
  {"init", jupsuper_init, METH_VARARGS, "Initialize"},
  {"release_bus", jupsuper_release_bus, METH_VARARGS, "Release bus"},
  {"take_bus", jupsuper_take_bus, METH_VARARGS, "Take the bus"},
  {"is_taken", jupsuper_is_taken, METH_VARARGS, "Returns true if bus is taken"},
  {"mem_read_start", jupsuper_mem_read_start, METH_VARARGS, "Start multiple memory reads"},
  {"mem_read_end", jupsuper_mem_read_end, METH_VARARGS, "End multiple memory reads"},
  {"mem_read_fast", jupsuper_mem_read_fast, METH_VARARGS, "Read one memory"},
  {"mem_read", jupsuper_mem_read, METH_VARARGS, "start, read, end"},
  {"mem_write_start", jupsuper_mem_write_start, METH_VARARGS, "Start multiple memory writes"},
  {"mem_write_end", jupsuper_mem_write_end, METH_VARARGS, "End multiple memory writes"},
  {"mem_write_fast", jupsuper_mem_write_fast, METH_VARARGS, "Write one memory"},
  {"mem_write_buffer", jupsuper_mem_write_buffer, METH_VARARGS, "Write one memory"},  
  {"mem_write", jupsuper_mem_write, METH_VARARGS, "start, write, end"},
  {"mem_snoop", jupsuper_mem_snoop, METH_VARARGS, "snoop the data bus"},
  {"port_read", jupsuper_port_read, METH_VARARGS, "start, read_port, end"},
  {"port_write", jupsuper_port_write, METH_VARARGS, "start, write_port, end"},  
  {"wait_signal", jupsuper_wait_signal, METH_VARARGS, "wait until woke"},
/*
  {"invert_hold", jupsuper_invert_hold, METH_VARARGS, "set invert hold"},
*/
  {"delay_mult", jupsuper_delay_mult, METH_VARARGS, "set delay mult"}, 
  {NULL, NULL, 0, NULL}
};

static struct PyModuleDef jupsuper_module =
{
    PyModuleDef_HEAD_INIT,
    "jupsuper_ext", /* name of module */
    "",          /* module documentation, may be NULL */
    -1,          /* size of per-interpreter state of the module, or -1 if the module keeps state in global variables. */
   jupsuper_methods
};

PyMODINIT_FUNC PyInit_jupsuper_ext(void)
{
  return PyModule_Create(&jupsuper_module);
}
