# birds — Birds on a Wire cipher

**Category:** crypto / encoding · **Flag:** `flag{thirteen}`

The challenge gives you `birds.png`: birds sitting at different heights on power
lines, with `{` and `}` drawn in. That styling is the giveaway — searching "birds on
a wire cipher" turns up the [Birds on a Wire cipher](https://www.dcode.fr/birds-on-a-wire-cipher).

### How it works

Each bird's **vertical position on the wire** encodes one letter (height → A–Z). It
is a simple substitution, so you read the birds left to right and map each to its
letter. The braces are drawn literally, so the shape is:

```
<4 birds> { <8 birds> }
```

### Solve

Decode the birds with dCode's "Birds on a Wire" tool (upload or recreate the
heights), or map them by hand. The four birds before `{` spell `flag`, and the eight
inside spell the word — which, fittingly for eight birds whose repeated positions
match the letter pattern t-h-i-**r**-t-e-e-n, is `thirteen`:

```
flag{thirteen}
```

**Lesson:** an unusual visual arrangement (birds, dancing men, pigpen shapes) is
usually a known pictorial substitution cipher — identify the cipher first, then map
symbols to letters.

## Debrief: what you learn and how to protect against it

**What you learn:** to recognise a pictorial cipher and search for its name before
trying to break it. "Birds on a wire" is a known substitution alphabet, like
pigpen or the dancing men. Finding out *what* you are looking at is most of the
work.

**The solve in short:**

1. Look at the picture: birds at different heights on the wires, with `{` and
   `}` drawn in, shaped like a flag.
2. Search for "birds on a wire cipher" and find the alphabet (dCode has it).
3. Map each bird to its letter, left to right.

**How to protect against it:**

- Swapping letters for pictures is still a monoalphabetic substitution, and a
  published one at that. A secret alphabet is not a key.
- This is Kerckhoffs's principle: a system must stay secure even when everything
  about it except the key is public. Use real encryption for real secrets.
