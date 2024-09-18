from setuptools import setup, find_packages

setup(
    name="infoservant",
    version="1.0.1",
    author="Mikhail Voloshin",
    author_email="mvol@mightydatainc.com",
    description="An AI that browses text content on the web. Easily integrate intelligent web surfing into any project.",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/Mighty-Data-Inc/webpage2content",
    packages=find_packages(),
    install_requires=[
        "openai",
        "serpapi",
        "webpage2content",
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.9",
    entry_points={
        "console_scripts": [
            "infoservant=infoservant.infoservant_impl:main",
        ],
    },
)
