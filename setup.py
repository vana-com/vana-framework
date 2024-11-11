from setuptools import setup, find_packages
from setuptools.command.install import install
from distutils.cmd import Command
from typing import Dict, Type, cast
import tomli
import subprocess
import sys

with open("pyproject.toml", "rb") as f:
    pyproject = tomli.load(f)

# Extract version and dependencies from pyproject.toml
version = pyproject["tool"]["poetry"]["version"]
dependencies = [
    # Convert poetry dependency specs to pip format
    f"{pkg}{ver.replace('^', '>=')}"
    for pkg, ver in pyproject["tool"]["poetry"]["dependencies"].items()
    if pkg != "python"
]


class PostInstallCommand(install):
    """Custom command that runs PATH setup after installation"""

    def run(self) -> None:
        """Run install and then update PATH"""
        install.run(self)
        try:
            # Run vanacli with post-install flag
            subprocess.run([sys.executable, "-m", "vana.cli", "--post-install"], check=True)
        except subprocess.CalledProcessError:
            print("Warning: Failed to update PATH configuration", file=sys.stderr)


command_classes = cast(Dict[str, Type[Command]], {
    'install': PostInstallCommand
})

setup(
    name="vana",
    version=version,
    packages=find_packages(),
    install_requires=dependencies,
    entry_points={
        'console_scripts': [
            'vanacli=vana.cli:main',
        ],
    },
    python_requires=pyproject["tool"]["poetry"]["dependencies"]["python"],
    cmdclass=command_classes
)
