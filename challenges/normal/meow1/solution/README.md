This is an introduction to connecting to linux servers using netcat.
Connection info is in the challenge description.

```bash
$ nc <host> <port>
Welcome to the first terminal challenge!

I'm not kitten around, just take a look to find the flag.

The current working directory is: /home/ctf
You are logged in as: ctf
```

In linux, we can use `ls` to list the files.

There is only one file on this server, named `flag.txt`.
We can use `cat` to print the contents of the file.

```bash
cat flag.txt
                                               .--.
                                               `.  \
                                                 \  \
                                                  .  \
                                                  :   .
                                                  |    .
                                                  |    :
                                                  |    |
  ..._  ___                                       |    |
 `."".`''''""--..___                              |    |
 ,-\  \             ""-...__         _____________/    |
 / ` " '                    `""""""""                  .
 \                                                      L
 (>                                                      \
/                                                         \
\_    ___..---.                                            L
  `--'         '.                                           \
                 .                                           \_
                _/`.                                           `.._
             .'     -.                                             `.
            /     __.-Y     /''''''-...___,...--------.._            |
           /   _."    |    /                ' .      \   '---..._    |
          /   /      /    /                _,. '    ,/           |   |
          \_,'     _.'   /              /''     _,-'            _|   |
                  '     /               `-----''               /     |
                  `...-'                                       `...-'
flag{R_u_k1tten_me}
```

## Debrief: what you learn and how to protect against it

**What you learn:** how to connect to a remote server with `nc` (netcat) and the
two commands everything else builds on: `ls` to list files and `cat` to print one.
It is the warm-up that makes sure everyone has a working terminal.

**The solve in short:**

1. Connect with `nc <host> <port>`.
2. `ls` shows a single file, `flag.txt`.
3. `cat flag.txt` prints the flag.

**How to protect against it:** there is no bug here, it is a skills task. The
real-world point is that whoever gets a shell on a server can read everything that
user can read.

- Don't expose a shell on an open port. Use SSH with keys (and MFA where you can).
- Keep secrets out of files the login user can read: tight file permissions and
  least privilege.
