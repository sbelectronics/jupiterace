: hex 16 base ! ;
: decimal 10 base ! ;
hex
55 constant fpdig01
57 constant fpdig23
59 constant fpdig45
5B constant fpblank

C0 fpblank out
12 fpdig45 out
34 fpdig23 out
56 fpdig01 out

: count1
  FFFF and
  dup 100 mod fpdig01 out
  dup 100 / fpdig23 out
  1+ ;

: count
  0
  begin
  count1
  0
  until
  ;

