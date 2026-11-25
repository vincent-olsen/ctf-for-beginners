# art — reverse image search (OSINT)

**Category:** OSINT · **Flag:** `flag{axel_knudsen_2021_sverdrups_gate_23}`

> ⚠️ This depends on live third-party state (a news article). Re-verify before each
> event — see the note at the end.

You get `art.png`, a photo of a street-art piece (a Google Street View capture; the
`AFK 2021` signature is readable in the image itself).

### Solve

1. Reverse image search it: [Google Images](https://images.google.com) → "Search by
   image" (or Google Lens), and upload `art.png`.
2. The match is this article:
   <https://www.splitcitymagazine.com/nyheter/provokatoren-afk>
3. The article gives the artist and the location; the year `2021` comes from the
   `AFK 2021` tag in the photo. Put them together:

   ```
   flag{axel_knudsen_2021_sverdrups_gate_23}
   ```

   Flags are case-insensitive, and the backup also accepts the name spelled
   `alex`/`aksel` and the street as `sverdrupsgate`.

**Lesson:** a photo carries searchable context (reverse image search), and visible
details in the image (a signature, a sign, a landmark) fill in the rest.

### Before the event
- The article at the URL above still resolves and still names the artist and the
  address (Sverdrups gate 23).
- Reverse image search still finds it from `art.png`.
- If the article is gone, host a local copy or swap the challenge; the flag depends
  on that page being reachable.

## Debrief: what you learn and how to protect against it

**What you learn:** OSINT (open-source intelligence): how much a single photo
gives away. Reverse image search finds where the picture has been published, and
details in the picture itself (a signature, a year, a street) fill in the rest.

**The solve in short:**

1. Upload `art.png` to a reverse image search (Google Lens / Google Images).
2. Open the article it finds, which names the artist and the address.
3. Read the year from the `AFK 2021` signature in the picture and put the three
   parts together in the flag format.

**How to protect against it:**

- Think about what is in a picture before you post it: street signs, house
  numbers, landmarks, name tags, screens and whiteboards in the background.
- Remove metadata (EXIF with GPS position and camera) before sharing. Many
  platforms do it for you, email and file sharing do not.
- For a company: have a rule for photos from the office, and assume an attacker
  uses exactly this technique to prepare phishing and social engineering.
