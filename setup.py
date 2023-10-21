import os
from setuptools import setup

# Utility function to read the README file.
# Used for the long_description.  It's nice, because now 1) we have a top level
# README file and 2) it's easier to type in the README file than to put a raw
# string in below ...
def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname), "r").read()

def get_version():
    g = {}
    exec(open(os.path.join("robotz", "Version.py"), "r").read(), g)
    return g["Version"]


setup(
    name = "robotz",
    version = get_version(),
    author = "Igor Mandrichenko",
    author_email = "igorvm@gmail.com",
    description = ("A set of useful tools built on top of standard Python threading module"),
    license = "BSD 3-clause",
    keywords = "threading, synchronization, multiprocessing, parallel computing",
    url = "https://github.com/imandr/robotz",
    packages=['robotz', 'tests'],
    long_description="A set of useful tools built on top of standard Python threading module", #read('README'),
    zip_safe = False,
    entry_points = { "console_scripts": [
                "director = director.director:main",
            ]
        },
    classifiers=[
        "Operating System :: POSIX",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Programming Language :: Python",
        "Topic :: Software Development :: Libraries",
        "Development Status :: 5 - Production/Stable",
        "Topic :: Utilities",
        "License :: OSI Approved :: BSD License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3"
    ]
)
