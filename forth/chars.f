: CHARS
  256 0
  DO
    I EMIT
  LOOP
;

( 11263 )
( 10495 )

: GR
  8 * 11263 + DUP
  8 +
  DO
    I C! -1
  +LOOP
;

2 BASE C!
: TRAIN
 00000100
 11110010
 00010010
 00011111
 00100001
 00100001
 11111111
 01100110
;
DECIMAL

: STUFF
 1 EMIT
 2 EMIT
 3 EMIT
 4 EMIT
;

CHARS
0 variable x
: test x ! 100 0 do 
  train x @ gr loop ;
