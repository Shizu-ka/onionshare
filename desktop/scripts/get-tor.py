#!/usr/bin/env python3
import platform
import inspect
import os
import sys
import hashlib
import shutil
import subprocess
import requests

# Windows
exe_url = (
    "https://dist.torproject.org/torbrowser/11.0.9/torbrowser-install-11.0.9_en-US.exe"
)
exe_filename = "torbrowser-install-11.0.9_en-US.exe"
expected_exe_sha256 = "e938433028b6ffb5d312db6268b19e419626b071f08209684c8e5b9f3d3df2bc"

# macOS
dmg_url = (
    "https://dist.torproject.org/torbrowser/11.0.9/TorBrowser-11.0.9-osx64_en-US.dmg"
)
dmg_filename = "TorBrowser-11.0.9-osx64_en-US.dmg"
expected_dmg_sha256 = "e34629a178a92983924a5a89c7a988285d2d27f21832413a7f7e33af7871c8d6"

# Linux
tarball_url = "https://dist.torproject.org/torbrowser/11.0.9/tor-browser-linux64-11.0.9_en-US.tar.xz"
tarball_filename = "tor-browser-linux64-11.0.9_en-US.tar.xz"
expected_tarball_sha256 = (
    "baa5ccafb5c68f1c46f9ae983b9b0a0419f66d41e0483ba5aacb3462fa0a8032"
)


# Common paths
root_path = os.path.dirname(
    os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
)
working_path = os.path.join(root_path, "build", "tor")


def get_tor_windows():
    # Build paths
    exe_path = os.path.join(working_path, exe_filename)
    dist_path = os.path.join(root_path, "onionshare", "resources", "tor")

    # Make sure the working folder exists
    if not os.path.exists(working_path):
        os.makedirs(working_path)

    # Make sure Tor Browser is downloaded
    if not os.path.exists(exe_path):
        print("Downloading {}".format(exe_url))
        r = requests.get(exe_url)
        open(exe_path, "wb").write(r.content)
        exe_sha256 = hashlib.sha256(r.content).hexdigest()
    else:
        exe_data = open(exe_path, "rb").read()
        exe_sha256 = hashlib.sha256(exe_data).hexdigest()

    # Compare the hash
    if exe_sha256 != expected_exe_sha256:
        print("ERROR! The sha256 doesn't match:")
        print("expected: {}".format(expected_exe_sha256))
        print("  actual: {}".format(exe_sha256))
        sys.exit(-1)

    # Extract the bits we need from the exe
    subprocess.Popen(
        [
            "7z",
            "e",
            "-y",
            exe_path,
            "Browser\\TorBrowser\\Tor",
            "-o%s" % os.path.join(working_path, "Tor"),
        ]
    ).wait()
    subprocess.Popen(
        [
            "7z",
            "e",
            "-y",
            exe_path,
            "Browser\\TorBrowser\\Data\\Tor\\geoip*",
            "-o%s" % os.path.join(working_path, "Data"),
        ]
    ).wait()

    # Copy into the onionshare resources
    if os.path.exists(dist_path):
        shutil.rmtree(dist_path)
    os.makedirs(dist_path)
    shutil.copytree(os.path.join(working_path, "Tor"), os.path.join(dist_path, "Tor"))
    shutil.copytree(
        os.path.join(working_path, "Data"), os.path.join(dist_path, "Data", "Tor")
    )

    # Fetch the built-in bridges
    update_tor_bridges()


def get_tor_macos():
    # Build paths
    dmg_tor_path = os.path.join(
        "/Volumes", "Tor Browser", "Tor Browser.app", "Contents"
    )
    dmg_path = os.path.join(working_path, dmg_filename)
    dist_path = os.path.join(root_path, "onionshare", "resources", "tor")
    if not os.path.exists(dist_path):
        os.makedirs(dist_path, exist_ok=True)

    # Make sure the working folder exists
    if not os.path.exists(working_path):
        os.makedirs(working_path)

    # Make sure the zip is downloaded
    if not os.path.exists(dmg_path):
        print("Downloading {}".format(dmg_url))
        r = requests.get(dmg_url)
        open(dmg_path, "wb").write(r.content)
        dmg_sha256 = hashlib.sha256(r.content).hexdigest()
    else:
        dmg_data = open(dmg_path, "rb").read()
        dmg_sha256 = hashlib.sha256(dmg_data).hexdigest()

    # Compare the hash
    if dmg_sha256 != expected_dmg_sha256:
        print("ERROR! The sha256 doesn't match:")
        print("expected: {}".format(expected_dmg_sha256))
        print("  actual: {}".format(dmg_sha256))
        sys.exit(-1)

    # Mount the dmg, copy data to the working path
    subprocess.call(["hdiutil", "attach", dmg_path])

    # Copy into dist
    shutil.copyfile(
        os.path.join(dmg_tor_path, "Resources", "TorBrowser", "Tor", "geoip"),
        os.path.join(dist_path, "geoip"),
    )
    shutil.copyfile(
        os.path.join(dmg_tor_path, "Resources", "TorBrowser", "Tor", "geoip6"),
        os.path.join(dist_path, "geoip6"),
    )
    shutil.copyfile(
        os.path.join(dmg_tor_path, "MacOS", "Tor", "tor.real"),
        os.path.join(dist_path, "tor"),
    )
    os.chmod(os.path.join(dist_path, "tor"), 0o755)
    shutil.copyfile(
        os.path.join(dmg_tor_path, "MacOS", "Tor", "libevent-2.1.7.dylib"),
        os.path.join(dist_path, "libevent-2.1.7.dylib"),
    )
    # obfs4proxy binary
    shutil.copyfile(
        os.path.join(dmg_tor_path, "MacOS", "Tor", "PluggableTransports", "obfs4proxy"),
        os.path.join(dist_path, "obfs4proxy"),
    )
    os.chmod(os.path.join(dist_path, "obfs4proxy"), 0o755)
    # snowflake-client binary
    shutil.copyfile(
        os.path.join(
            dmg_tor_path, "MacOS", "Tor", "PluggableTransports", "snowflake-client"
        ),
        os.path.join(dist_path, "snowflake-client"),
    )
    os.chmod(os.path.join(dist_path, "snowflake-client"), 0o755)

    # Eject dmg
    subprocess.call(["diskutil", "eject", "/Volumes/Tor Browser"])

    # Fetch the built-in bridges
    update_tor_bridges()


def get_tor_linux():
    # Build paths
    tarball_path = os.path.join(working_path, tarball_filename)
    dist_path = os.path.join(root_path, "onionshare", "resources", "tor")

    # Make sure dirs exist
    if not os.path.exists(working_path):
        os.makedirs(working_path, exist_ok=True)

    if not os.path.exists(dist_path):
        os.makedirs(dist_path, exist_ok=True)

    # Make sure the tarball is downloaded
    if not os.path.exists(tarball_path):
        print("Downloading {}".format(tarball_url))
        r = requests.get(tarball_url)
        open(tarball_path, "wb").write(r.content)
        tarball_sha256 = hashlib.sha256(r.content).hexdigest()
    else:
        tarball_data = open(tarball_path, "rb").read()
        tarball_sha256 = hashlib.sha256(tarball_data).hexdigest()

    # Compare the hash
    if tarball_sha256 != expected_tarball_sha256:
        print("ERROR! The sha256 doesn't match:")
        print("expected: {}".format(expected_tarball_sha256))
        print("  actual: {}".format(tarball_sha256))
        sys.exit(-1)

    # Delete extracted tarball, if it's there
    shutil.rmtree(os.path.join(working_path, "tor-browser_en-US"), ignore_errors=True)

    # Extract the tarball
    subprocess.call(["tar", "-xvf", tarball_path], cwd=working_path)
    tarball_tor_path = os.path.join(
        working_path, "tor-browser_en-US", "Browser", "TorBrowser"
    )

    # Copy into dist
    shutil.copyfile(
        os.path.join(tarball_tor_path, "Data", "Tor", "geoip"),
        os.path.join(dist_path, "geoip"),
    )
    shutil.copyfile(
        os.path.join(tarball_tor_path, "Data", "Tor", "geoip6"),
        os.path.join(dist_path, "geoip6"),
    )
    shutil.copyfile(
        os.path.join(tarball_tor_path, "Tor", "tor"),
        os.path.join(dist_path, "tor"),
    )
    os.chmod(os.path.join(dist_path, "tor"), 0o755)
    shutil.copyfile(
        os.path.join(tarball_tor_path, "Tor", "libcrypto.so.1.1"),
        os.path.join(dist_path, "libcrypto.so.1.1"),
    )
    shutil.copyfile(
        os.path.join(tarball_tor_path, "Tor", "libevent-2.1.so.7"),
        os.path.join(dist_path, "libevent-2.1.so.7"),
    )
    shutil.copyfile(
        os.path.join(tarball_tor_path, "Tor", "libssl.so.1.1"),
        os.path.join(dist_path, "libssl.so.1.1"),
    )
    shutil.copyfile(
        os.path.join(tarball_tor_path, "Tor", "libstdc++", "libstdc++.so.6"),
        os.path.join(dist_path, "libstdc++.so.6"),
    )
    shutil.copyfile(
        os.path.join(tarball_tor_path, "Tor", "PluggableTransports", "obfs4proxy"),
        os.path.join(dist_path, "obfs4proxy"),
    )
    os.chmod(os.path.join(dist_path, "obfs4proxy"), 0o755)
    shutil.copyfile(
        os.path.join(
            tarball_tor_path, "Tor", "PluggableTransports", "snowflake-client"
        ),
        os.path.join(dist_path, "snowflake-client"),
    )
    os.chmod(os.path.join(dist_path, "snowflake-client"), 0o755)

    print(f"Tor binaries extracted to: {dist_path}")

    # Fetch the built-in bridges
    update_tor_bridges()


def update_tor_bridges():
    """
    Update the built-in Tor Bridges in OnionShare's torrc templates.
    """
    torrc_template_dir = os.path.join(
        root_path, os.pardir, "cli/onionshare_cli/resources"
    )
    endpoint = "https://bridges.torproject.org/moat/circumvention/builtin"
    r = requests.post(
        endpoint,
        headers={"Content-Type": "application/vnd.api+json"},
    )
    if r.status_code != 200:
        print(
            f"There was a problem fetching the latest built-in bridges: status_code={r.status_code}"
        )
        return False

    result = r.json()

    if "errors" in result:
        print(
            f"There was a problem fetching the latest built-in bridges: errors={result['errors']}"
        )
        return False

    for bridge_type in ["meek-azure", "obfs4", "snowflake"]:
        if result[bridge_type]:
            if bridge_type == "meek-azure":
                torrc_template_extension = "meek_lite_azure"
            else:
                torrc_template_extension = bridge_type
            torrc_template = os.path.join(
                root_path,
                torrc_template_dir,
                f"torrc_template-{torrc_template_extension}",
            )

            with open(torrc_template, "w") as f:
                f.write(f"# Enable built-in {bridge_type} bridge\n")
                bridges = result[bridge_type]
                # Sorts the bridges numerically by IP, since they come back in
                # random order from the API each time, and create noisy git diff.
                bridges.sort(key=lambda s: s.split()[1])
                for item in bridges:
                    f.write(f"Bridge {item}\n")


def main():
    """
    Download Tor Browser and extract tor binaries
    """
    system = platform.system()
    if system == "Windows":
        get_tor_windows()
    elif system == "Darwin":
        get_tor_macos()
    elif system == "Linux":
        get_tor_linux()
    else:
        print("Platform not supported")


if __name__ == "__main__":
    main()