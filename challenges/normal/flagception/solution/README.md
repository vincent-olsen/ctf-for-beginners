# flagception — maritime signal flags

**Category:** crypto / encoding · **Flag:** `flag{inj3cti0s_sql}`

`flags.png` is a row of **nautical signal flags** — the challenge name ("flag-ception":
flags made of flags) is the hint. Each International Code of Signals flag stands for
one letter, and the numeric **pennants** stand for digits.

### Solve

Look up the [International maritime signal flags](https://en.wikipedia.org/wiki/International_maritime_signal_flags)
chart and read the row left to right, flag by flag. Letter flags give letters,
number pennants give digits (`3` and `0` appear here), which spells:

```
FLAG{INJ3CTI0S_SQL}
```

Flags are matched case-insensitively, so `flag{inj3cti0s_sql}` is accepted. (Note the
intended spelling is `inj3cti0s`, without an "n".)

**Lesson:** signal flags are just another alphabet — recognise the flag set, then map
each glyph (and the number pennants) to its character.

## Debrief: what you learn and how to protect against it

**What you learn:** the international maritime signal flags, one flag per letter
and one pennant per digit. As in `birds`, the skill is to identify a known
symbol alphabet and look it up.

**The solve in short:**

1. Recognise the row of nautical signal flags (the name "flag-ception" is the
   hint: a flag made of flags).
2. Find the chart of the International Code of Signals.
3. Read the row left to right, letter flags as letters and pennants as digits.

**How to protect against it:**

- Signal flags are an encoding made to be read by everyone, not a way to keep
  something secret. An unusual alphabet only slows down someone who has not
  searched for it yet.
- Secrets need a key: encrypt with a standard cipher and keep the key separate.
