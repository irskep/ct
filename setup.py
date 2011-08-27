from distutils.core import setup

setup(
    name="cuttime",
    version="0.1",
    provides=["cuttime"],
    author="Steve Johnson",
    author_email="steve@steveasleep.com",
    url="http://github.com/irskep/ct",
    description='Time tracking tool',
    classifiers=[
        "Programming Language :: Python",
        "Operating System :: OS Independent",
    ],
    packages=["cuttime"],
    requires=["dateutil (==1.5)"],
    scripts=['bin/ct'],
    long_description="""cut time - a time tracking tool
"""
)

