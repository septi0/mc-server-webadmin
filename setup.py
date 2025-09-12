from setuptools import setup

info = {}

with open("mcadmin/info.py") as fp:
    exec(fp.read(), info)

version = ""
with open("mcadmin/VERSION", "r") as f:
    version = f.read().strip()

with open("README.md", "r") as f:
    long_description = f.read()

with open("requirements.txt") as f:
    requirements = [line.strip() for line in f]

setup(
    name=info["__package_name__"],
    version=version,
    description=info["__description__"],
    long_description=long_description,
    long_description_content_type="text/markdown",
    license=info["__license__"],
    author=info["__author__"],
    author_email=info["__author_email__"],
    author_url=info["__author_url__"],
    python_requires=">=3.10",
    install_requires=requirements,
    packages=[
        "mcadmin",
        "mcadmin.endpoints",
        "mcadmin.libraries",
        "mcadmin.libraries.mc_server",
        "mcadmin.middlewares",
        "mcadmin.models",
        "mcadmin.schemas",
        "mcadmin.services",
        "mcadmin.utils",
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: POSIX :: Linux",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Topic :: Utilities",
    ],
    entry_points={
        "console_scripts": [
            "mc-server-webadmin = mcadmin:main",
        ],
    },
    include_package_data=True,
    package_data={
        "mcadmin": [
            "migrations/**/*",
            "static/**/*",
            "templates/*",
            "VERSION",
        ],
    },
)
