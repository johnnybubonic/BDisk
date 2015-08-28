#
# /etc/bash.bashrc
#

# If not running interactively, don't do anything
[[ $- != *i* ]] && return

PS1='[\u@\h \W]\$ '
PS2='> '
PS3='> '
PS4='+ '

case ${TERM} in
  xterm*|rxvt*|Eterm|aterm|kterm|gnome*)
    PROMPT_COMMAND=${PROMPT_COMMAND:+$PROMPT_COMMAND; }'printf "\033]0;%s@%s:%s\007" "${USER}" "${HOSTNAME%%.*}" "${PWD/#$HOME/\~}"'

    ;;
  screen)
    PROMPT_COMMAND=${PROMPT_COMMAND:+$PROMPT_COMMAND; }'printf "\033_%s@%s:%s\033\\" "${USER}" "${HOSTNAME%%.*}" "${PWD/#$HOME/\~}"'
    ;;
esac

[ -r /usr/share/bash-completion/bash_completion   ] && . /usr/share/bash-completion/bash_completion

alias vi='/usr/bin/vim'
export EDITOR="vim"

if [ -f ~/.bashrc ];
then
 source ~/.bashrc
fi 
if [ -d ~/bin ];
then
 export PATH="$PATH:~/bin"
fi

alias grep='grep --color'
alias egrep='egrep --color'

alias ls='ls --color=auto'
PS1='[\u@\h \W]\$ '

export HISTTIMEFORMAT="%F %T "
export PATH="${PATH}:/sbin:/bin:/usr/sbin"

DEFROUTEIF=$(ip route show | egrep '^default' | awk '{print $5}')

echo
echo "==================================="
date
if [ -n "${DEFROUTEIF}" ];
then
 IPADDR=$(ip a s dev ${DEFROUTEIF} | egrep '^[[:space:]]*inet\ ' | awk '{print $2}' | cut -f1 -d"/")
 HWADDR=$(ip l show dev ${DEFROUTEIF} | egrep '^[[:space:]]*link' | awk '{print $2}')
 echo
 echo -n "${DEFROUTEIF} (${HWADDR}) is: ${IPADDR}"
fi
echo
echo  -n "tun0 is:"
ifconfig tun0 | grep inet | grep -v "inet6" | awk '{print $2}'
echo
echo "http://bdisk.square-r00t.net/"
echo "==================================="
echo
