function join_by { local IFS="$1"; shift; echo "$*"; }
function denon {
    join_by $'\n' "$@"
    join_by $'\n' "$@" | telnet 'Denon-AVR-X1400H' 23 >/dev/null 2>&1
}

