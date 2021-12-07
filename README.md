# jellyshuf 
Essentially implements ncmpcpp's add random feature (default hotkey: `) through a script which grabs info from jellyfin api itself. 
jellyfin-mpd (and by proxy jellyfin-mopidy) does not implement the required mpd commands for this ncmpcpp function to work. 

# Install
## Arch Linux (AUR)
`paru -S jellyshuf` (or any other AUR helper) 

## Any system (pip)
`pip install jellyshuf` 

or

```
git clone https://github.com/deafmute1/jellyshuf.git
cd jellyshuf
pip install . 
```

# Usage
jellyshuf will asked for required information config info on first run (server url, username, password, cache settings).
This info is stored to `$XDG_CONFIG_DIR/jellyshuf/user.json`. At the moment, the password is stored in plaintext in this file. In future, it will support use of keyrings.

Note: This program currently requires the option `albumartistsort` in mopidy-jellyfin to be set to `true` (this is the default setting).

`jellyshuf --help` 
```
USAGE: jellyshuf <FLAGS> TYPE NUMBER
    
TYPE is one of artists, albums, songs 
    
FLAGS: 
    --stdout        Instead of adding retrieved paths to mpd queue, emits them to stdout (line separated)
    --random|-r     Set mpd to random mode after adding new items
    --start|-s      Start mpd after adding new items
    --clear|-c      Clear mpd queue before adding items
    --config        Run config (overwriting any existing info) then exit
    --help|-h       Display this message and exit
```
