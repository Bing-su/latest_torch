import os
import platform
import re
from dataclasses import dataclass
from urllib.parse import unquote
from urllib.request import urlopen

from setuptools import setup
from setuptools.extern import packaging

# Check
system = platform.system()
machine = platform.machine()
impl = platform.python_implementation()

if (system.lower(), machine.lower()) not in [
    ("windows", "amd64"),
    ("darwin", "x86_64"),
    ("darwin", "arm64"),
    ("linux", "x86_64"),
    ("linux", "aarch64"),
]:
    msg = f"Unsupported platform, machine: ({system}, {machine})"
    raise RuntimeError(msg)

if impl.lower() != "cpython":
    msg = f"Unsupported python implementation: {impl}"
    raise RuntimeError(msg)


parse = packaging.version.parse
Version = packaging.version.Version


@dataclass
class WheelInfo:
    name: str
    version: str
    backend: str
    pyver: str
    platform: str

    _version: Version
    url: str


# Get all wheel info
WHEEL_INFO_RE = re.compile(
    r"""^(?P<namever>(?P<name>[^\s-]+?)-(?P<ver>[^\s-]+?))(-(?P<build>\d[^\s-]*))?
     -(?P<pyver>[^\s-]+?)-(?P<abi>[^\s-]+?)-(?P<plat>\S+)\.whl$""",
    re.VERBOSE,
)


url_base = "https://download.pytorch.org/whl"
raw_html: str = urlopen(f"{url_base}/torch_stable.html").read().decode("utf-8")
all_wheel = []
for line in raw_html.splitlines():
    wheel = re.search(r">([^>]+)</a>", line)
    if not wheel:
        continue

    name = unquote(wheel.group(1))
    name = name.split("/")[-1]

    if not re.search(r"(torch|torchvision|torchaudio)-", name):
        continue

    wheel_info = WHEEL_INFO_RE.match(name)
    if not wheel_info:
        continue

    name_ = wheel_info.group("name")
    ver = wheel_info.group("ver")
    pyver = wheel_info.group("pyver")
    plat = wheel_info.group("plat")

    version = parse(ver)

    info = WheelInfo(
        name=name_,
        version=version.public,
        backend=version.local or "cpu",
        pyver=pyver,
        platform=plat,
        _version=version,
        url=f"{url_base}/{wheel.group(1)}",
    )

    all_wheel.append(info)


# Filter wheel
current_pyver = "cp" + "".join(platform.python_version_tuple()[:2])
backend = os.getenv("LATEST_TORCH_BACKEND", "cuda").lower()
if backend == "cuda":
    backend = "cu"

if backend in ("cu", "rocm"):
    all_backends = {
        info.backend
        for info in all_wheel
        if info.backend.startswith(backend) and not info.backend.endswith("cudnn")
    }

    def key(v: str):
        v = re.sub(r"[\D\.]", "", v)
        return tuple(map(int, v.split(".")))

    backend = max(all_backends, key=key)

plat_map = {
    "windows": "win",
    "darwin": "macosx",
    "linux": "linux",
}
plat = plat_map[system.lower()]
arch = machine.lower()

matching_wheels = [
    info
    for info in all_wheel
    if info.pyver == current_pyver
    and info.backend == backend
    and plat in info.platform
    and arch in info.platform
]

if not matching_wheels:
    msg = f"No matching wheel found for {current_pyver}, {backend}, {system}, {machine}"
    raise RuntimeError(msg)

torch_wheels = [info for info in matching_wheels if info.name == "torch"]
torchvision_wheels = [info for info in matching_wheels if info.name == "torchvision"]
torchaudio_wheels = [info for info in matching_wheels if info.name == "torchaudio"]

info_string = "{name} @ {url}"
extras_require = {}

if torch_wheels:
    torch_wheel = max(torch_wheels, key=lambda info: info._version)
    install_requires = [info_string.format(name="torch", url=torch_wheel.url)]
else:
    msg = f"No torch wheel found for {current_pyver}, {backend}, {system}, {machine}"
    raise RuntimeError(msg)

if torchvision_wheels:
    torchvision_wheel = max(torchvision_wheels, key=lambda info: info._version)
    extras_require["torchvision"] = info_string.format(
        name="torchvision", url=torchvision_wheel.url
    )

if torchaudio_wheels:
    torchaudio_wheel = max(torchaudio_wheels, key=lambda info: info._version)
    extras_require["torchaudio"] = info_string.format(
        name="torchaudio", url=torchaudio_wheel.url
    )


setup(
    install_requires=install_requires,
    extras_require=extras_require,
)
