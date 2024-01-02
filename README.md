# Scott's Jupiter Ace Stuff
https://www.smbaker.com/

# Boards

You can find the following boards here. Each subdirectory contains the schematic and the gerbers.

* other. Contains other usefile files, such as the edge card connector used to make piggyback cards.

* ram. Memory expansion board. Adds 48K to bring the RAM up to maximum. With some additional work
  in the PLD, could support 4 banks for a total of 192KB of RAM.

* pi. Raspberry Pi Bus Supervisor. This can take control of the Jupiter Ace's Bus by asserting the
  BUSREQ signal. Once in control, it can read/write memory or operate on IO ports. It can inject
  characters into the keyboard buffer and press return. It can do this with entire files to load
  a whole file via the console. It can also load TAP and ACE files directly into RAM.

* speech. Speech synthesizer that is more-or-less compatible with the bigmouth speech synthesizers.
  Uses the sp0256A-AL2 speech synthesis IC.
