#!/usr/bin/env bash

[[ -z "$1" ]] && {
  cat <<EOF2 >&2
  usage: $0 <CHALLENGE-NAME | PATH>
  Example:
    ./local.sh meow1
    ./local.sh robot-ai
    ./local.sh challenges/normal/meow1
EOF2
  exit 1
}

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$REPO/tools/challenge.sh"

# A bare name is looked up under challenges/*/; a path is used as given.
resolve_challenge "$1" || exit 1
challenge=$CHALLENGE_NAME
dir=$CHALLENGE_DIR
dockerfile="$dir/challenge/Dockerfile"

if [[ ! -f "$dockerfile" ]]; then
  echo "Dockerfile not found: ${dockerfile#"$REPO"/}" >&2
  exit 1
fi

# Use the same host port as compose.yml (what ctf.sh and the docs use);
# challenges without a compose service map their EXPOSE port 1:1.
ports=$(compose_ports "$dir")
if [[ -z "$ports" ]]; then
  port=$(grep -i '^EXPOSE' "$dockerfile" | awk '{print $2}' | head -n1)
  if [[ -z "$port" ]]; then
    echo "No EXPOSE found in ${dockerfile#"$REPO"/}" >&2
    exit 1
  fi
  ports="$port:$port"
fi

echo "Running $challenge on localhost:${ports%%:*}" >&2
docker build "$dir/challenge/" -t "$challenge"
docker run --name "$challenge" --rm -p "$ports" "$challenge"
