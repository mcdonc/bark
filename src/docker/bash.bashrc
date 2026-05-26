# shellcheck shell=bash
# System-wide bash defaults for Bark containers.
# Users can override these in ~/.bashrc on the persistent home mount.

# Wait for the entrypoint to finish setup before showing a prompt.
# Prevents races where the user runs pi before config files are ready.
# /tmp is a tmpfs, so .bark-ready is cleared on every container start.
while [ ! -f /tmp/.bark-ready ]; do sleep 0.1; done

PS1='\[\033[01;34m\]\w\[\033[00m\]\$ '
HISTFILE=~/.bash_history
HISTSIZE=1000
HISTFILESIZE=2000
shopt -s histappend
PROMPT_COMMAND="history -a"
alias ls='ls --color=auto'
alias grep='grep --color=auto'
