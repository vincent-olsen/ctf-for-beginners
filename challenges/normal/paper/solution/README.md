# paper

The flag is printed on an A5 card hidden in the venue. Find the card, type the
flag (or scan the QR code on it, which holds the same text) and submit it in the
challenge `paper`. Only the first team to submit gets the points: the challenge
has `max_solves: 1`, so it locks after one solve.

## For the organiser

1. Print `challenge/paper-flag.pdf` on A4, two-sided, at 100 % ("actual size",
   not "fit to page"). Page 1 is the front with the flag, page 2 the back
   without it. The card in the middle is A5 (148 x 210 mm), centred, so the
   sides line up whichever edge the printer flips on.
2. Cut along the crop marks.
3. Hide the card before the event starts, somewhere it can be found without
   moving or opening anything (the description promises that).
4. Keep the PDF and the printout away from players: it is the answer.

To change the flag, edit `challenge/flag.txt` and the `flag:` in `metadata.yml`,
then rebuild the card (see the top of `challenge/make-card.py`).

If the card is found by someone who is not playing, or goes missing, hide the
challenge in the admin panel. To let a second team in, raise `max_solves` and
run `./ctf.sh up`.

## Debrief: what you learn and how to protect against it

- **What you learn:** security is not only software. Passwords on sticky notes,
  printouts left on a printer, a badge on a desk and documents in a paper bin
  are all found by someone who simply looks around. Attackers who walk into an
  office do exactly that.
- **The solve in short:** look around the venue, find the card, submit the flag
  before anyone else does.
- **The defence:** a clean desk policy, shredding sensitive paper, pull printing
  (the job prints only when you badge in at the printer), never writing
  credentials down, and questioning strangers who wander around the office.
