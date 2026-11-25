FROM debian:12

RUN apt update -y && \
apt install socat -y && \
apt clean -y

RUN useradd -m ctf -u1001

ADD bashrc /home/ctf/.bashrc

RUN mkdir -p /home/ctf/one
ADD fake1.txt /home/ctf/one/this.txt
ADD fake2.txt /home/ctf/one/or_this1.txt
ADD fake3.txt /home/ctf/one/or_this2.txt
ADD fake4.txt /home/ctf/one/or_this3.txt
ADD fake1.txt /home/ctf/one/or_this4.txt
ADD fake2.txt /home/ctf/one/or_this5.txt
ADD fake1.txt /home/ctf/one/or_this6.txt
ADD fake3.txt /home/ctf/one/or_this7.txt
ADD fake2.txt /home/ctf/one/or_this8.txt
ADD fake4.txt /home/ctf/one/or_this9.txt
ADD fake2.txt /home/ctf/one/or_this10.txt

RUN mkdir -p /home/ctf/two
ADD fake3.txt /home/ctf/two/or_this1.txt
ADD fake2.txt /home/ctf/two/or_this2.txt
ADD fake4.txt /home/ctf/two/or_this3.txt
ADD fake2.txt /home/ctf/two/or_this4.txt
ADD fake1.txt /home/ctf/two/or_this5.txt
ADD fake2.txt /home/ctf/two/or_this6.txt
ADD fake1.txt /home/ctf/two/or_this7.txt
ADD fake3.txt /home/ctf/two/or_this8.txt
ADD fake4.txt /home/ctf/two/or_this9.txt
ADD fake2.txt /home/ctf/two/or_this10.txt

RUN mkdir -p /home/ctf/three
ADD fake1.txt /home/ctf/three/or_this1.txt
ADD fake3.txt /home/ctf/three/or_this2.txt
ADD fake2.txt /home/ctf/three/or_this3.txt
ADD fake1.txt /home/ctf/three/or_this4.txt
ADD fake4.txt /home/ctf/three/or_this5.txt
ADD fake2.txt /home/ctf/three/or_this6.txt
ADD fake1.txt /home/ctf/three/or_this7.txt
ADD fake3.txt /home/ctf/three/or_this8.txt
ADD fake3.txt /home/ctf/three/or_this9.txt
ADD fake2.txt /home/ctf/three/or_this10.txt

RUN mkdir -p /home/ctf/four
ADD fake2.txt /home/ctf/four/or_this1.txt
ADD fake1.txt /home/ctf/four/or_this2.txt
ADD fake3.txt /home/ctf/four/or_this3.txt
ADD fake4.txt /home/ctf/four/or_this4.txt
ADD fake1.txt /home/ctf/four/or_this5.txt
ADD fake3.txt /home/ctf/four/or_this6.txt
ADD fake2.txt /home/ctf/four/or_this7.txt
ADD fake2.txt /home/ctf/four/or_this8.txt
ADD fake2.txt /home/ctf/four/or_this9.txt
ADD fake3.txt /home/ctf/four/or_this10.txt

RUN mkdir -p /home/ctf/five
ADD fake1.txt /home/ctf/five/or_this1.txt
ADD fake2.txt /home/ctf/five/or_this2.txt
ADD fake1.txt /home/ctf/five/or_this3.txt
ADD fake3.txt /home/ctf/five/or_this4.txt
ADD fake4.txt /home/ctf/five/or_this5.txt
ADD fake2.txt /home/ctf/five/or_this6.txt
ADD fake2.txt /home/ctf/five/or_this7.txt
ADD fake3.txt /home/ctf/five/or_this8.txt
ADD fake1.txt /home/ctf/five/or_this9.txt
ADD fake1.txt /home/ctf/five/or_this10.txt

RUN mkdir -p /home/ctf/six
ADD fake1.txt /home/ctf/six/or_this1.txt
ADD fake3.txt /home/ctf/six/or_this2.txt
ADD fake2.txt /home/ctf/six/or_this3.txt
ADD fake1.txt /home/ctf/six/or_this4.txt
ADD fake2.txt /home/ctf/six/or_this5.txt
ADD fake4.txt /home/ctf/six/or_this6.txt
ADD fake2.txt /home/ctf/six/or_this7.txt
ADD fake2.txt /home/ctf/six/or_this8.txt
ADD flag.txt /home/ctf/six/or_this9.txt
ADD fake3.txt /home/ctf/six/or_this10.txt

RUN mkdir -p /home/ctf/seven
ADD fake1.txt /home/ctf/seven/or_this1.txt
ADD fake3.txt /home/ctf/seven/or_this2.txt
ADD fake1.txt /home/ctf/seven/or_this3.txt
ADD fake4.txt /home/ctf/seven/or_this4.txt
ADD fake2.txt /home/ctf/seven/or_this5.txt
ADD fake1.txt /home/ctf/seven/or_this6.txt
ADD fake2.txt /home/ctf/seven/or_this7.txt
ADD fake2.txt /home/ctf/seven/or_this8.txt
ADD fake3.txt /home/ctf/seven/or_this9.txt
ADD fake4.txt /home/ctf/seven/or_this10.txt

RUN mkdir -p /home/ctf/eight
ADD fake1.txt /home/ctf/eight/or_this1.txt
ADD fake2.txt /home/ctf/eight/or_this2.txt
ADD fake2.txt /home/ctf/eight/or_this3.txt
ADD fake3.txt /home/ctf/eight/or_this4.txt
ADD fake4.txt /home/ctf/eight/or_this5.txt
ADD fake3.txt /home/ctf/eight/or_this6.txt
ADD fake2.txt /home/ctf/eight/or_this7.txt
ADD fake2.txt /home/ctf/eight/or_this8.txt
ADD fake1.txt /home/ctf/eight/or_this9.txt
ADD fake3.txt /home/ctf/eight/or_this10.txt

RUN mkdir -p /home/ctf/nine
ADD fake1.txt /home/ctf/nine/or_this1.txt
ADD fake2.txt /home/ctf/nine/or_this2.txt
ADD fake1.txt /home/ctf/nine/or_this3.txt
ADD fake2.txt /home/ctf/nine/or_this4.txt
ADD fake1.txt /home/ctf/nine/or_this5.txt
ADD fake3.txt /home/ctf/nine/or_this6.txt
ADD fake2.txt /home/ctf/nine/or_this7.txt
ADD fake1.txt /home/ctf/nine/or_this8.txt
ADD fake2.txt /home/ctf/nine/or_this9.txt
ADD fake4.txt /home/ctf/nine/or_this10.txt

RUN mkdir -p /home/ctf/ten
ADD fake3.txt /home/ctf/ten/or_this1.txt
ADD fake2.txt /home/ctf/ten/or_this2.txt
ADD fake1.txt /home/ctf/ten/or_this3.txt
ADD fake2.txt /home/ctf/ten/or_this4.txt
ADD fake3.txt /home/ctf/ten/or_this5.txt
ADD fake4.txt /home/ctf/ten/or_this6.txt
ADD fake2.txt /home/ctf/ten/or_this7.txt
ADD fake2.txt /home/ctf/ten/or_this8.txt
ADD fake3.txt /home/ctf/ten/or_this9.txt
ADD fake1.txt /home/ctf/ten/or_this10.txt

RUN chown -R root:ctf /home/ctf

USER 1001

EXPOSE 4445

ENTRYPOINT ["socat", "-T900", "TCP-LISTEN:4445,reuseaddr,fork", "EXEC:'/bin/bash -li',pty,stderr,setsid,sane"]
