import setuptools

MODULE_NAME    = "pcbzip"                                                       # The python module name
VERSION        = "3.3"                                                          # The version of the application
AUTHOR         = "Paul Austen"                                                  # The name of the applications author
AUTHOR_EMAIL   = "pausten.os@gmail.com"                                         # The email address of the author
DESCRIPTION    = "A tool to package Kicad gerber files for MFG."                # A short description of the application
LICENSE        = "MIT License"                                                  # The License that the application is distributed under
REQUIRED_LIBS  = ["pillow>=9.0.0"]                                              # A python list of required libs (optionally including versions)

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name=MODULE_NAME,
    version=VERSION,
    author=AUTHOR,
    author_email=AUTHOR_EMAIL,
    description=DESCRIPTION,
    long_description="",                                                        #This will be read from the README.md file
    long_description_content_type="text/markdown",
    packages=setuptools.find_packages(),
    include_package_data=True,
    package_data={'': ['jlcpcb_kicad_v6_plot.png', 'jlcpcb_kicad_v6_drill.png','jclpcb_kicad_v6_placement.png']},
    classifiers=[
        "License :: %s" % (LICENSE),
        "Operating System :: OS Independent",
    ],
    install_requires=[
        REQUIRED_LIBS
    ],
    scripts=['scripts/pcbzip']
)
