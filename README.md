# bcpi
__Griffin Milsap (griffin.milsap@jhuapl.edu)__  
__Johns Hopkins University Applied Physics Lab__  
Brain Computer (Human) Interface Device platform with embedded deployment to Raspberry Pi  

## Run
```
usage: bcpi [-h] [--config CONFIG] [--only-core] [--single-process] [--create-config]
            [--install] [--uninstall]

bcpi - Brain Computer Interface on the Raspberry Pi

optional arguments:
  -h, --help        show this help message and exit
  --config CONFIG   config path for bcpi (default = /home/bcpi/.config/bcpi, or set
                    BCPI_CONFIG)
  --only-core       launch the minimal (core) subset of functionality for realtime
                    inferencing
  --single-process  ensure all units run in single process (lower memory footprint)
  --create-config   create a config file at --config and exit
  --install         install systemd services to start an ezmsg graphserver and bcpi at
                    system boot
  --uninstall       uninstall bcpi-related systemd services
```

## Configuration

`bcpi --create-config`

This creates `~/.config/bcpi/bcpi.conf` which looks like this:

```
# configuration for bcpi
# all defaults are commented out

[bcpi]
# directory for storing recordings, models, and strategies
#data_dir = ~/bcpi-data

# port for hosting web dashboard on
#port = 8888

[ezmsg]
# bcpi can connect to remote ezmsg GraphServers
# default behavior looks for a graphserver at localhost:25978
# and if it doesn't exist, it'll spawn one on localhost at a random port.
# the default setting enforces connection to the canonical local graphserver 
# (as spawned by `ezmsg serve`), but you can run bcpi on a sandboxed/isolated
# graphserver spawned at runtime by setting:
#   graphserver = any

#graphserver = localhost:25978

[unicorn]
# if included, this is the address ezmsg-unicorn will
# repeatedly look for a device to connect to.
#address = simulator
#n_samp = 50
```

### `[unicorn]` Section

Currently, `bcpi` only works with g.tec Unicorn devices as input.  It can be especially valuable to set a device address for your g.tec Unicorn device in this file, so that it autoconnects when running `bcpi` in headless mode (`--only-core`).  To get this address, run `bluetoothctl` on your RPi, then type `scan on` and turn on your Unicorn by holding the button for a few seconds.  Once the device status LED is blinking blue, you should eventually see an advertisement that looks like

```
[NEW] Device 60:B6:47:E1:26:9E 60-B6-47-E1-26-9E
[CHG] Device 60:B6:47:E1:26:9E Name: UN-2023.03.64
[CHG] Device 60:B6:47:E1:26:9E Alias: UN-2023.03.64
```

All Unicorn devices advertise a bluetooth device name of the format `UN-XXXX.XX.XX`, and the associated Bluetooth address here is of the format XX:XX:XX:XX:XX:XX.  In this example, the `address` line in the `[unicorn]` section would be set like so:

```
[unicorn]
# if included, this is the address ezmsg-unicorn will
# repeatedly look for a device to connect to.
address = 60:B6:47:E1:26:9E
#n_samp = 50
```
__Note that the hash (#) has been removed from the address line to indicate this is a non-default setting.__

## PC Install
`bcpi` is fully functional on PCs.  It can be useful to run on PC and train/develop control strategies before deploying to RPi for headless inferencing.   
* ```pip install git+https://github.com/griffinmilsap/bcpi.git```

## Embedded (Raspberry Pi) Install (WIP)

`bcpi` is purpose-built for Raspberry Pi embedded compute environments.  
Much of this setup might be workable for other Linux single board computers, but YMMV.  
Development experience is best on the Pi 4+ but Pi Zero 2 W has been successfully tested as well.

1. Grab latest Raspberry Pi 64 bit OS version without Desktop
    1. Download Raspberry Pi Imager
    1. `Choose OS`
    1. `Raspberry Pi OS (other)`
    1. `Raspberry Pi OS Lite (64-bit)`
1. Choose an SD card (choose storage)
1. Click the Gear in the lower right corner
    1. Set hostname: `bcpi##.local` (`##` should be a unique hostname; mine is `01`)
    1. Enable SSH with password authentication
    1. Set Username: `bcpi` and Password: (I like `bcpi2000`)
    1. Configure Wireless Lan (Only works for home WiFi; enterprise (work) wifi config comes later)
    1. Set locale settings
1. __Flash SD Card__
1. Insert SD card into Raspberry Pi
1. Power on Raspberry Pi

### If Pi doesn't (or can't connect to the wifi network/no SSH yet)
1. Use HDMI and USB adapters for video and mouse/keyboard input to Raspberry Pi
1. Use `raspi-config` to (re)set WiFi settings and reboot.
1. (Optional; only relevant to APLers) -- * [To connect to JHUAPL-Staff, follow instructions here (requires intranet access)](https://aplwiki.jhuapl.edu/confluence/display/LAPLKEY/Connect+Raspberry+Pi+to+JHUAPL-Staff+using+CLI)
1. Reboot and disconnect HDMI and USB adapters; use SSH to access the RPi from a PC on the same WiFi network from here on out.
    ``` bash
    ssh bcpi@bcpi.local
    ```

### Once you can SSH (as user `bcpi`) into Raspberry Pi
1. `sudo apt update`
1. `sudo apt upgrade` (might take a bit)
1. `sudo apt install ufw`
1. `sudo apt install python3-venv`

### Install [`ezmsg-gadget`](https://github.com/griffinmilsap/ezmsg-gadget)
One of the most valuable bits of functionality that `bcpi` provides is USB HID device emulation for BCI interactions with un-modified systems.  This functionality is provided by [`ezmsg-gadget`](https://github.com/griffinmilsap/ezmsg-gadget) using "USB Gadget" mode which is only supported on some Raspberry Pi platforms.  The only supported platforms are the Raspberry Pi 4+, the CM4, and the Pi Zero//2W.  This is accomplished with a device-tree overlay applied on boot and a kernel-mode driver that enables this gadget mode functionality.  This is likely to be done VERY differently if you're deploying to a different embedded system environment (i.e. not RPi).

See: https://github.com/griffinmilsap/ezmsg-gadget?tab=readme-ov-file#install
    1. __Don't install the endpoint service (omit `--install-endpoint-service`); that conflicts with `bcpi`.__

### Clone a bunch of repositories
1. Within a directory in the home directory (`mkdir ~/repos`)
    1. `git clone https://github.com/griffinmilsap/bcpi`
    1. (Optional) `git clone https://github.com/iscoe/ezmsg`
    1. (Optional) `git clone https://github.com/griffinmilsap/ezmsg-panel`
    1. (Optional) `git clone https://github.com/griffinmilsap/ezmsg-gadget`
    1. (Optional) `git clone https://github.com/griffinmilsap/ezmsg-tasks`
    1. (Optional) `git clone https://github.com/griffinmilsap/ezmsg-unicorn`
1. (Optional) Clone `ezmsg-fbcsp` (repository is private for reasons)
    1. Get repo access from [griffinmilsap](https://github.com/griffinmilsap)
    1. Create a personal access token that can be used to clone the repo
        1. Access your github [personal access token settings](https://github.com/settings/tokens)
        1. Create a classic personal access token (YMMV with Fine-grained tokens) with the `repo` scope, named for your `bcpi##` hostname
        1. Copy the token (will only be given to you once) which likely starts with `ghp_`
    1. Create a file on the Raspberry Pi: `~/.netrc` and write the following to it:
        ``` bash
        machine github.com login [your github username] password [token]
        ```
    1. Finally, clone `ezmsg-fbcsp` which should work without password now
        1. `git clone https://github.com/iscoe/ezmsg-fbcsp` 
1. (Optional) Create a script that makes it easy to update all of these repos.  In `~/repos`, create a file called `pull_all.sh` and make it executable `chmod +x pull_all.sh`
    ``` bash
    #! /usr/bin/env bash
    ls -R -d */.git | cut -d'.' -f1 | xargs -I{} git -C {} pull
    ```

### Set up bcpi virtual environment
1. `python3 -m venv ~/env --system-site-packages`
1. Within (env): `source env/bin/activate`
    1. `pip install --upgrade pip`
    1. `pip install poetry`
    1. `pip install -e ~/repos/bcpi`
    1. (Optional) `pip install -e ~/repos/ezmsg-fbcsp`
    1. (Optional) That last install command will bring in a lot of repositories and do non-editable installs of those dependencies; many of which are repositories we might want to have development installs of.  If you'd like a development (editable) install of these repositories; ensure they're all cloned in `~/repos`
        1. For every repository in `~/repos`:
            ``` bash
            cd ~/repos/[repo] && pip install -e . --no-deps
            ```
        1. Check that you have repos editably installed by executing `pip list` (versions might be different than this output)
            ```
            ...
            bcpi                 0.2.0        /home/bcpi/repos/bcpi
            ...
            ezmsg                3.3.3        /home/bcpi/repos/ezmsg
            ezmsg-fbcsp          0.3.0        /home/bcpi/repos/ezmsg-fbcsp
            ezmsg-gadget         0.2.0        /home/bcpi/repos/ezmsg-gadget
            ezmsg-panel          0.3.1        /home/bcpi/repos/ezmsg-panel
            ezmsg-sigproc        1.2.3        /home/bcpi/repos/ezmsg/extensions/ezmsg-sigproc
            ezmsg-tasks          0.1.0        /home/bcpi/repos/ezmsg-tasks
            ezmsg-unicorn        0.2.0        /home/bcpi/repos/ezmsg-unicorn
            ...
            ```

### Install/Configure `bcpi`
(The following instructions might soon be obviated by executing `bcpi install`)

1. `ln -s ~/env/bin/bcpi ~/bcpi`
1. `sudo ufw allow 8888/tcp`
1. As superuser, create `/lib/systemd/system/ezmsg.service` that will start an `ezmsg` graphserver on boot.
    ```
    [Unit]
    Description=GraphServer for ezmsg
    After=network.target

    [Service]
    Type=oneshot
    User=bcpi
    ExecStart=/home/bcpi/env/bin/python -m ezmsg.core start
    RemainAfterExit=true
    ExecStop=ezmsg shutdown
    StandardOutput=journal

    [Install]
    WantedBy=local-fs.target
    ```
1. As superuser, create `/lib/systemd/system/bcpi.service` that will start `bcpi`
    ```
    [Unit]
    Description=BCI development environment for Raspberry Pi
    After=syslog.target
    Requires=ezmsg-gadget.service
    Requires=ezmsg.service

    [Service]
    Type=simple
    User=bcpi
    WorkingDirectory=/home/bcpi
    ExecStart=/home/bcpi/env/bin/bcpi 
    StandardOutput=journal

    [Install]
    WantedBy=local-fs.target
    ```
    __PRO TIP:__ The Pi Zero 2W is underpowered to deliver a compelling UI//frontend experience.
   Change the `ExecStart` line to `ExecStart=/home/bcpi/env/bin/bcpi --only-core --single-process` for the Pi Zero 2W.
1. `sudo systemctl daemon-reload`
1. `sudo systemctl enable ezmsg.service`
1. `sudo systemctl enable bcpi.service`
1. Within the `bcpi` virtual environment: (`source ~/env/bin/activate`)
    1. `bcpi --create-config`  
    This creates `~/.config/bcpi/bcpi.conf` where you can configure the way the `bcpi` app works.  See the "Config" section.
1. (Optional) Allow the `bcpi` user to shutdown the system without password authentication.  This enables the Shutdown and Reboot buttons in the Panel dashboard.
    1. Create a file called `shutdown` in `/etc/sudoers.d` with the following contents.  
    Note, if you're doing this manually; make sure you use   
    `sudo visudo /etc/sudoers.d/shutdown`
        ```
        ## bcpi user is allowed to execute halt and reboot
        bcpi ALL=NOPASSWD: /sbin/halt, /sbin/reboot, /sbin/poweroff
        ```

### Optional Quality of Life Improvements
On low resource platforms (Raspberry Pi Zero 2W), it can be handy to run an instance of Jupyter Lab to upload pre-trained models and develop/deploy strategies.  

1. Within the bcpi virtual environment: `source ~/env/bin/activate`
    1. `pip install jupyterlab`
    1. `jupyter lab --generate-config`
    1. `jupyter lab password` (then enter a password for Jupyter)
1. As superuser, create `/lib/systemd/system/jupyter.service`
    ```
    [Unit]
    Description=Jupyter Lab

    [Service]
    Type=simple
    PIDFile=/run/jupyter.pid
    ExecStart=/bin/bash -c "/home/bcpi/env/bin/jupyter-lab --ip="0.0.0.0" --port=8888 --no-browser --notebook-dir=/home/bcpi"
    User=bcpi
    Group=bcpi
    WorkingDirectory=/home/bcpi
    Restart=always
    RestartSec=10

    [Install]
    WantedBy=multi-user.target
   ```
1. `sudo systemctl daemon-reload`
1. To start Jupyter Lab, simply `sudo systemctl start jupyter.service`.  

You might find that your Raspberry Pi platform doesn't have enough memory to run `bcpi` and JupyterLab at the same time (looking at you, Pi Zero 2W).  Additionally, the default `bcpi` port is set to `8888` which conflicts with the Jupyter Lab service as defined above (see the `ExecStart` line defines the port as `8888`).  It can be useful to shutdown `bcpi.service` and start `jupyter.service` as a so-called "developer mode".  You can make this easy by creating a `~/developer.sh` with the following contents.  Make sure you make the file executable too (`chmod +x ~/developer.sh`)
``` bash
#! /usr/bin/env bash

systemctl stop bcpi.service
systemctl start jupyter.service
```

Then you can `sudo ./developer.sh` to turn on Jupyter Lab "Developer Mode".  If you find yourself doing this more often than not, you might save yourself a bit of time by disabling `bcpi.service` on boot and enabling `jupyter.service` on boot.
``` bash
sudo systemctl disable bcpi.service
sudo systemctl enable jupyter.service
```
