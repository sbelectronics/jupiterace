100 VARIABLE QUAVER

: N QUAVER @ * BEEP ;
: PART1
  190 3 N 213 3 N 239 6 N
;
: PART2 
  159 3 N 179 2 N 179 1 N
  190 5 N
;
: PART3
  159 1 N 119 2 N 119 1 N
  127 1 N 142 1 N 127 1 N
  119 2 N 159 1 N 159 2 N
;
: MICE
  PART1 PART1
  PART2 119 1 N
  PART2
  PART3 PART3 PART3
  179 1 N PART1
;