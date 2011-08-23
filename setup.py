from distutils.core import setup

setup(
    name="companytime",
    version="0.1",
    provides=["companytime"],
    author="Steve Johnson",
    author_email="steve@steveasleep.com",
    url="http://github.com/irskep/ct",
    description='Time tracking tool',
    classifiers=[
        "Programming Language :: Python",
        "Operating System :: OS Independent",
    ],
    packages=["companytime"],
    requires=["dateutil (==1.5)"],
    scripts=['bin/ct'],
    long_description="""companytime - a time tracking tool
"""
)

