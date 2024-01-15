: hex 16 base ! ;
: decimal 10 base ! ;
hex
51 constant clkin_port
51 constant clkout_port
53 constant clkaddr_port
55 constant fpdig01
57 constant fpdig23
59 constant fpdig45
5B constant fpblank
0 constant clks1
1 constant clks10
2 constant clkm1
3 constant clkm10
4 constant clkh1
5 constant clkh10
6 constant clkd1
7 constant clkd10
8 constant clkmo1
9 constant clkmo10
A constant clky1
B constant clky10
C constant clkW
D constant clkCD
E constant clkCE
F constant clkCF

: zeros begin dup 0> while
  30 emit 1- repeat drop ;

: clk_addr clkaddr_port out ;

: clk_inp clk_addr clkin_port
  in F and ;

: clk_outp clkout_port out ;

: clk_in clk_addr 0 begin
  drop clkin_port in dup
  clkin_port in = until
  F AND ;

: clk_out clk_addr
  clkout_port out ;

: clk_sec clks10 clk_in
  10 * clks1 clk_in + ;

: clk_min clkm10 clk_in
  10 * clkm1 clk_in + ;

: clk_hour clkh10 clk_in
  10 * clkh1 clk_in + ;

: clk_sec_set dup 10 /
  clks10 clk_out F and clks1
  clk_out ;

: clk_min_set dup 10 /
  clkm10 clk_out F and clkm1
  clk_out ;

: clk_hour_set dup 10 /
  clkh10 clk_out F and clkh1
  clk_out ;

: clk_once_term clk_hour
  u. 3A EMIT clk_min
  u. 3A EMIT clk_sec
  u. ;

: clk_init 0 clkCF clk_out
  0 clkCD clk_out ;

: disp_enable C0 fpblank out ;

: disp_sec fpdig01 out ;

: disp_min fpdig23 out ;

: disp_hour fpdig45 out ;

: clk_once clk_hour disp_hour
  clk_min disp_min clk_sec
  disp_sec ;

: clk_forever disp_enable begin
  clk_once 0 until ;
