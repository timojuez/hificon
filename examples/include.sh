function denon() {
    `dirname $(readlink -f $0)`/denon.py "$@"
}

