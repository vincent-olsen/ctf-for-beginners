"""Preview mode: a few challenges anyone can play without a CTFd account.

`./ctf.sh up --preview julius,meow1` hides every other challenge and makes the
board public; platform/ctfd_admin.py keeps the preview's challenge ids in the
CTFd config value "ctf_preview". Stock CTFd shows a public board to anonymous
visitors, but answers their flags with "authentication_required" and the theme
sends them to the login page. While the config value is set, this plugin
answers those attempts instead:

    POST /api/v1/challenges/attempt    checked like CTFd does, nothing is saved

for the preview's own challenges only, in CTFd's response shape, so the stock
challenge window shows "Correct" or "Incorrect" as usual. Wrong flags are
limited per IP address, as CTFd limits them per account. The index page, which
in the imported backups belongs to a past event, redirects to the board.
Logged-in users (the admin) go through CTFd as usual.

The implementation is in preview.py, which is imported only in load(): CTFd
doesn't catch a plugin's errors, so if it doesn't fit this CTFd version the
plugin switches itself off instead of stopping CTFd from starting. Visitors can
then still see the board, but have to log in to submit a flag.

ctf.sh copies this folder into CTFd/plugins/ while a preview is set and removes
it when the preview is turned off.
"""


def load(app):
    try:
        from .preview import before_request

        app.before_request(before_request)
    except Exception as e:  # noqa: BLE001 - never take CTFd down with us
        print(" * ctf_preview disabled, anonymous flag checks are off: %r" % (e,))
