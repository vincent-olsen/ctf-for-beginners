### QR codes

**Solution**

You could scan each indiviual image on the gif with your phone and get the flag, or you could download the imagemagic and zbar-tools

```jsx
sudo apt-get update
sudo apt-get install imagemagick
sudo apt-get install zbar-tools
```

Then you can read every image out

```jsx
mkdir img
convert qrcode.gif -coalesce img/xx_%05d.png
cd img
```

```jsx
$ zbarimg *.png
QR-Code:f
QR-Code:l
QR-Code:a
QR-Code:g
QR-Code:{
QR-Code:4
QR-Code:b
QR-Code:a
QR-Code:k
QR-Code:0
QR-Code:$
QR-Code:}
scanned 12 barcode symbols from 12 images in 0.42 seconds
```

## Debrief: what you learn and how to protect against it

**What you learn:** that an animated GIF is a stack of single frames, and how to
automate a boring job: split the frames with ImageMagick and read all the QR
codes with `zbarimg`, instead of scanning twelve times with a phone.

**The solve in short:**

1. Open the GIF: each frame is a QR code holding one character.
2. Split it: `convert qrcode.gif -coalesce img/xx_%05d.png`.
3. Read every frame: `zbarimg img/*.png`, and put the characters together.

**How to protect against it:** there is no bug here, it is a skills task. The
real-world points about QR codes:

- A QR code is plain text that people cannot read by eye, which makes it popular
  for phishing ("quishing"). Look at the URL your phone shows before you open it,
  and be sceptical of codes on stickers and in emails.
- Don't put secrets in a QR code and think they are hidden. A photo of a
  boarding pass, a ticket or an MFA setup code gives away everything in it.
