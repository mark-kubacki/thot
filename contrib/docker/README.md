# containerized Thot

Run `build.sh` to get a container image `localhost/thot`.
If you are Mark, or intend to upload the resulting image, this is how you
can change the *host* part of its name:

```bash
env D="rg.nl-ams.scw.cloud/mark" ./build.sh
```

## BASH alias

With this in your `~/.bash_aliases` (I use `podman` – change this to `docker` if you are old-school)

```bash
thot() {
  podman run -ti --rm --read-only \
    --net=host --user 0:0 \
    -v "${PWD}":/srv \
    "localhost/thot" \
      "$@"
}
```

## everyday use

… it is merely a calling (change directory names):

```bash
cd /tmp
thot --quickstart "myblog"

cd /tmp/"myblog"
thot
```
