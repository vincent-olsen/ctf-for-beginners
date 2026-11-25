# unk — a corrupted Word document

**Category:** forensics · **Flag:** `flag{old_macdonald_or_mcdonalds_supplier?}`

You get a file called `unk` with no extension that won't open. Check its type:

```bash
$ file unk
unk: Zip archive data, ... method=deflate
```

It's a zip. A `.docx` is just a zip of XML, and this is one with a **corrupted first
entry** — its local-header signature has been overwritten, which is why viewers call
it a "damaged archive". `unzip` reports the bad first entry but recovers the rest:

```bash
$ unzip unk
Archive:  unk
file #1:  bad zipfile offset (local header sig):  0
  inflating: _rels/.rels
  inflating: word/_rels/document.xml.rels
  inflating: word/document.xml
  inflating: word/theme/theme1.xml
 extracting: docProps/thumbnail.jpeg
  inflating: word/settings.xml
  ... (the other OOXML parts)
```

`unzip` exits with an error code because of that first entry, but every other file
is extracted. Only `[Content_Types].xml` (the clobbered first entry) is lost; the
document body survives.

The flag is in the document text, in `word/document.xml`. A plain
`grep 'flag{' word/document.xml` only shows `flag{`, though: Word splits the text
into several runs, so the flag is broken up by XML tags:

```
...<w:t>flag{</w:t>...<w:t>old_macdonald_or_mcdonalds_supplier</w:t>...<w:t>?</w:t>...<w:t>}</w:t>
```

Strip the tags first, then search:

```bash
$ sed -e 's/<[^>]*>//g' word/document.xml | grep -o 'flag{[^}]*}'
flag{old_macdonald_or_mcdonalds_supplier?}
```

Without the `grep`, `sed -e 's/<[^>]*>//g' word/document.xml` prints the whole
text: the Old MacDonald lyrics, with the flag at the end.

The same flag is also legible in the preview image `docProps/thumbnail.jpeg` if you
prefer to just look at it.

**Lesson:** Office documents are zip archives; a single corrupted header makes them
"unopenable" while the real content extracts fine with `unzip`, and the text lives in
`word/document.xml`.

## Debrief: what you learn and how to protect against it

**What you learn:** to identify a file by its content with `file` instead of
trusting its name, that an Office document (`.docx`) is a zip archive of XML, and
that a "damaged" archive usually still gives up most of its content.

**The solve in short:**

1. `file unk` says it is a zip archive.
2. `unzip unk` complains about the first entry and extracts the rest.
3. The text is in `word/document.xml`. Strip the XML tags and search:
   `sed -e 's/<[^>]*>//g' word/document.xml | grep -o 'flag{[^}]*}'`.

**How to protect against it:**

- Corrupt or "unopenable" does not mean gone. If a file must be unreadable,
  encrypt it or wipe it properly. Breaking the header only stops a double-click.
- Documents carry more than the visible text: a thumbnail of the first page,
  author names, comments and old revisions. Use the document inspector (or
  export to a clean PDF) before sending a document out.
- For services that receive files: decide the type from the content (magic
  bytes), never from the extension.
