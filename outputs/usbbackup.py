import os
import subprocess


def unmount(mediadir):
    # Unmount USB
    for name in os.listdir(mediadir):
        full = os.path.join(mediadir, name)
        if os.path.ismount(full):
            print("Unmounting: " + full)
            subprocess.Popen(["sudo", "umount", full])


def mounted(mediadir):
    # Get a list of usb devices plugged in
    deviceList = checkusb()
    if not deviceList:
        # If there are no connected USB then unmount any mount points
        # print("Nothing to see here")
        unmount(mediadir)
    else:
        # Mount the first usb device if not mounted already
        device = deviceList[0]
        name = os.path.basename(device)
        mountdir = os.path.join(mediadir, name)
        if not os.path.exists(mountdir):
            subprocess.Popen(["sudo", "mkdir", mountdir])
        if not os.path.ismount(mountdir):
            print("Mounting: " + mountdir)
            try:
                cmd = 'sudo mount -o rw,umask=0022,uid=1000,gid=1000 %s %s' % (device, mountdir)
                output = subprocess.check_output(cmd, shell=True)
                returncode = 0
                #cmd = 'sudo chmod 775 %s' % (mountdir)
            except subprocess.CalledProcessError as e:
                output = e.output
                returncode = e.returncode
                raise output
                return None
    # Return found mount point
    return mountdir


def checkusb():
    # Find any connected USB memory
    idPath = '/dev/disk/by-id/'
    deviceList = []
    for name in os.listdir(idPath):
        if "usb" in name:
            if "part" in name:
                full = os.path.join(idPath, name)
                if os.path.islink(full):
                    realpath = os.path.realpath(full)
                    deviceList = deviceList + [realpath]
    return deviceList


def main(local, remote):
    # Back up to USB
    # Get mountpoint
    mount = mounted(remote)
    # If a USB is plugged in, then rsync the data to USB
    if mount is not None:
        print("Backing up to USB")
        rsync_cmd = 'rsync -varz %s/ %s/' % (local, mount)

        p = subprocess.Popen(rsync_cmd, shell=True).wait()
        if p == 0:
            print("Backup Success")
            return True
        else:
            print("Backup Failed")
            return False
    else:
        print("No USB plugged in")
        return False

if __name__ == '__main__':
    media = "/media"
    ld = "~/logs"
    main(ld, media)
