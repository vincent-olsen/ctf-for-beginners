"""Hints in order: a hint can't be bought before the hints it requires.

platform/ctfd_admin.py (_sync_hints) gives every hint the challenge's strictly
cheaper hints as its prerequisites, so a player unlocks the cheapest first. CTFd
checks a hint's prerequisites when it is opened (GET /api/v1/hints/<id>, which
the challenge window calls before it offers the unlock), but not when it is
bought: a plain

    POST /api/v1/unlocks    {"type": "hints", "target": <id>}

buys any hint, and the challenge then hands its text over as one of the
account's unlocked hints. This plugin answers that request first when the
account lacks one of the hint's prerequisites, with the error CTFd gives for
opening such a hint, so the challenge window and the theme's translation show
it the same way. It also keeps a retired hint (its own prerequisite, see
_sync_hints) from being bought.

The implementation is in order.py, which is imported only in load(): CTFd
doesn't catch a plugin's errors, so if it doesn't fit this CTFd version the
plugin switches itself off instead of stopping CTFd from starting. The
challenge window still keeps the order then; only the direct request gets
through.

ctf.sh copies this folder into CTFd/plugins/ on every `./ctf.sh up`.
"""


def load(app):
    try:
        from .order import before_request

        app.before_request(before_request)
    except Exception as e:  # noqa: BLE001 - never take CTFd down with us
        print(" * ctf_hints disabled, a hint's prerequisites are not checked on purchase: %r" % (e,))
