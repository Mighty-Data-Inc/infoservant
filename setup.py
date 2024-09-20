import os
from setuptools import setup, find_packages

# Read the version from the VERSION file
with open(
    os.path.join(os.path.dirname(__file__), "infoservant/VERSION"), "r"
) as version_file:
    version = version_file.read().strip()


setup(
    name="infoservant",
    version=version,
    author="Mikhail Voloshin",
    author_email="mvol@mightydatainc.com",
    description="An AI that browses text content on the web. Can conduct deep-dives. Easily integrate intelligent web researching into any project.",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/Mighty-Data-Inc/infoservant",
    packages=find_packages(),
    install_requires=[
        "google-search-results",
        "openai",
        "python-dotenv",
        "webpage2content",
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.9",
    entry_points={
        "console_scripts": [
            "infoservant=infoservant.infoservant_impl:main",
        ],
    },
    license="Apache-2.0",
    package_data={
        "infoservant": ["VERSION"],
    },
    include_package_data=True,
)
