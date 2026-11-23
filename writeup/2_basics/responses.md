# Section 2: Basics

## 2.2.1 Docker ensures reproducibility

**Problem 1 (`docker-setup`)**

1. Paste the commands you used to pull `ubuntu:22.04` and start an interactive container, followed by the output from inside the container that confirms its operating system (e.g., `cat /etc/os-release`).

   ```text
   $ docker pull ubuntu:22.04
22.04: Pulling from library/ubuntu
f74d428f3a50: Pull complete
f1ed2c25af57: Download complete
Digest: sha256:f64b2ffc2f10ab8f8505aa56b2664bd846cbb9df87c7e2532e30f7667021c0e6
Status: Downloaded newer image for ubuntu:22.04
docker.io/library/ubuntu:22.04

$ docker run -it ubuntu:22.04
root@b3b70b65455b:/# cat /etc/os-release
PRETTY_NAME="Ubuntu 22.04.5 LTS"
NAME="Ubuntu"
VERSION_ID="22.04"
VERSION="22.04.5 LTS (Jammy Jellyfish)"
VERSION_CODENAME=jammy
ID=ubuntu
ID_LIKE=debian
HOME_URL="https://www.ubuntu.com/"
SUPPORT_URL="https://help.ubuntu.com/"
BUG_REPORT_URL="https://bugs.launchpad.net/ubuntu/"
PRIVACY_POLICY_URL="https://www.ubuntu.com/legal/terms-and-policies/privacy-policy"
UBUNTU_CODENAME=jammy
root@b3b70b65455b:/# exit
   ```

## 2.2.2 Harbor defines evaluation primitives

**Problem 2 (`harbor-setup`)**

1. Paste the output of `uv run harbor --version` and `docker version`.

   ```text
   $ uv run harbor --version
0.18.0

$ docker version
Client:
 Version:           29.9.2
 API version:       1.56
 Go version:        go1.26.10
 Git commit:        a82e528
 Built:             Tue Oct 20 18:43:59 2026
 OS/Arch:           darwin/arm64
 Context:           desktop-linux

Server: Docker Desktop 4.97.0 (244584)
 Engine:
  Version:          29.9.2
  API version:      1.56 (minimum version 1.40)
  Go version:       go1.26.10
  Git commit:       0367cbe
  Built:            Tue Oct 20 18:44:14 2026
  OS/Arch:          linux/arm64
  Experimental:     false
 containerd:
  Version:          v2.4.2
  GitCommit:        b7a25261e029d68978bbf290df0a62fc819b3c51
 runc:
  Version:          1.5.2
  GitCommit:        v1.5.2-0-g29dd3dc2
 docker-init:
  Version:          0.19.0
  GitCommit:        de40ad0
   ```

2. From `uv run harbor --help`, which commands start an evaluation job and browse completed results?

   `harbor run` starts an evaluation job. The help output describes it as "Start a job. Alias for `harbor job start`", and `harbor exec` can also compile paths into tasks and run a job. `harbor view` browses completed results: it "starts a web server to browse trajectory files", so I can open each attempt's trajectory, verifier logs and reward. `harbor hub` also lets you view jobs, tasks and trials, but on the Harbor Hub rather than from local files.
