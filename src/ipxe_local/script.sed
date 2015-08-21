s/^#undef([[:space:]]*NET_PROTO_IPV6)/#define\1/g
s/^#undef([[:space:]]*DOWNLOAD_PROTO_HTTPS)/#define\1/g
s/^#undef([[:space:]]*DOWNLOAD_PROTO_FTP)/#define\1/g
s@^//(#define[[:space:]]*CONSOLE_CMD)@\1@g
#s@^//(#define[[:space:]]*IMAGE_MULTIBOOT)@\1@g
#s@^//(#define[[:space:]]*IMAGE_SCRIPT@\1@g
s@^//(#define[[:space:]]*IMAGE_PNG@\1@g
#s@^//(#define[[:space:]]*IMAGE_TRUST_CMD@\1@g
