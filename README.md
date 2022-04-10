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
jellyshuf will asked for required information config info on first run. Some advanced config options are not exposed via `jellyshuf --config`. You can edit these manually. You can use `--empty-config` to generate all options with their defaults at the config location. The config file is located at  `$XDG_CONFIG_DIR/jellyshuf/config.json`. 

Passwords is by default stored to the system keyring if available; otherwise, they are stored in the config file as plaintext.

Please note there is some time required to fetch items from jellyfin when they have not yet been cached to disk. This is mainly noticable with using `songs`; on large libraries there may be notcable lag even when using disk cache. Subsonic implementation which makes use of the ability to set the size of the return list, and to offload randomisation of songs to the server does not have this issue.

This program currently requires the option `albumartistsort` in mopidy-jellyfin to be set to `true` (this is the default setting).

`jellyshuf --help` 
```
usage: jellyshuf [-h] [--stdout] [-i] [-r] [-s] [-c] [--config] [--default-config] [-v] backend size type

Randomly add items to mpd queue from jellyfin or subsonic server.

positional arguments:
  backend            Server backend to use (either subsonic/sonic/ss or jellyfin/jf)
  size               Number of items to add to queue
  type               Type of items to add (either albums, artists or songs)

options:
  -h, --help         show this help message and exit
  --stdout           Instead of adding retrieved paths to mpd queue, emits them to stdout (line separated)
  -i, --interactive  If not in stdout mode, interactively confirms albums before adding them; jellyshuf runs until NUMBER has been added to queue.
  -r, --random       Set mpd to random mode after adding new items
  -s, --start        Start mpd after adding new items
  -c, --clear        Clear mpd queue before adding items
  --config           Run interactive config (overwriting existing settings on disk), then exit
  --default-config   Replace config on disk with default one
  -v, --version      Print version and exit    

```

## Backend support.
- Jellyfin backend: Offically supports Emby API reference; tested working on the following implementations: Jellyfin 
- (Sub)sonic backend: Officially supports Subsonic API reference; tested working on follow implementations: Navidrome