from setuptools import setup, find_packages
import tomli

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
)
