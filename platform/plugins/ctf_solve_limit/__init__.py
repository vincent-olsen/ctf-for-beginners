"""Solve limits: a challenge that locks once enough teams have solved it.

A challenge with `max_solves: N` in its metadata.yml (`paper`, a flag printed on
paper and hidden in the venue: `max_solves: 1`) can be solved by N accounts
only. platform/ctfd_admin.py keeps the limits in the CTFd config value
"ctf_solve_limit" as {"<challenge id>": N}. Stock CTFd has a limit on attempts,
not on solves, so while that value lists a challenge this plugin

  - answers POST /api/v1/challenges/attempt for it once N visible accounts
    (not hidden, not banned; a team in teams mode) have solved it, in CTFd's
    response shape, so the challenge window shows the message. Nothing is
    saved and no attempt is counted. An account that solved it gets CTFd's own
    "already solved", and an admin goes through CTFd as usual;
  - serves GET /solve-limit/status: every visible limited challenge with its
    limit, whether it is locked and who solved it, which
    platform/theme/solve-limit.js shows on the board and in the challenge
    window.

Two correct flags sent in the same instant can both get in, as the check and
CTFd's save are two steps.

The implementation is in limit.py, which is imported only in load(): CTFd
doesn't catch a plugin's errors, so if it doesn't fit this CTFd version the
plugin switches itself off instead of stopping CTFd from starting. A limited
challenge can then be solved by everyone who has its flag.

ctf.sh copies this folder into CTFd/plugins/ on every `./ctf.sh up`.
"""


def load(app):
    try:
        from .limit import before_request, solve_limit

        app.before_request(before_request)
        app.register_blueprint(solve_limit)
    except Exception as e:  # noqa: BLE001 - never take CTFd down with us
        print(" * ctf_solve_limit disabled, max_solves is not enforced: %r" % (e,))
