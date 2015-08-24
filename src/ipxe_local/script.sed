s/^#undef([[:space:]]*NET_PROTO_IPV6)/#define\1/g
## currently broken for EFI building
#s/^#undef([[:space:]]*DOWNLOAD_PROTO_HTTPS)/#define\1/g
s/^#undef([[:space:]]*DOWNLOAD_PROTO_FTP)/#define\1/g
s@^//(#define[[:space:]]*CONSOLE_CMD)@\1@g
# causing hangs? seems to cause linux kernels to crash
#s@^//(#define[[:space:]]*IMAGE_MULTIBOOT)@\1@g
# still have no idea what this does.
#s@^//(#define[[:space:]]*IMAGE_SCRIPT@\1@g
s@^//(#define[[:space:]]*IMAGE_PNG@\1@g
# save this for when we enable signed/trusted loading
#s@^//(#define[[:space:]]*IMAGE_TRUST_CMD@\1@g
