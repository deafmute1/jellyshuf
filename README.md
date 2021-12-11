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
Some advanced config options are not exposed via `jellyshuf --config`. You can edit these manually. You can use `--empty-config` to generate all options with their defaults at the config location.
The config file is located at  `$XDG_CONFIG_DIR/jellyshuf/config.json`. 
The jellyfin password is by default stored to the system keyring if available.

Please note there is some time required to fetch items from jellyfin when they have not yet been cached to disk. This is mainly noticable with using `songs`; on large libraries there may be notcable lag even when using disk cache.

This program currently requires the option `albumartistsort` in mopidy-jellyfin to be set to `true` (this is the default setting).

`jellyshuf --help` 
```
USAGE: jellyshuf <FLAGS> TYPE NUMBER
    
TYPE is one of artists, albums, songs 
    
FLAGS: 
    --stdout            Instead of adding retrieved paths to mpd queue, emits them to stdout (line separated)
    --interactive|-i    If not in stdout mode, interactively confirms albums before adding them;
                            jellyshuf runs until NUMBER has been added to queue.
    --random|-r         Set mpd to random mode after adding new items
    --start|-s          Start mpd after adding new items
    --clear|-c          Clear mpd queue before adding items
    --config            Run config (overwriting any existing info) then exit
    --empty-config      Generate an empty config file at config location.
    --version           Print version and exit
    --help|-h           Display this message and exit
```
