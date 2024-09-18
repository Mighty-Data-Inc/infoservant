These instructions will guide you through the process of setting up a Python package called `infoservant` that you can distribute on PyPI. This will include creating the package structure, writing the necessary code, and setting up the packaging and distribution files.

### Step 1: Create the Project Structure

First, create the directory structure for your project:

```
infoservant/
├── infoservant/
│   ├── __init__.py
│   └── infoservant.py
├── tests/
│   └── test_infoservant.py
├── README.md
├── setup.py
└── MANIFEST.in
```

### Step 2: Write the Code

Create the `infoservant/infoservant.py` file with the following content:

```python
import requests
from bs4 import BeautifulSoup

def infoservant(url):
    response = requests.get(url)
    response.raise_for_status()  # Raise an error for bad status codes
    soup = BeautifulSoup(response.text, 'html.parser')
    return soup.get_text()
```

Create the `infoservant/__init__.py` file with the following content:

```python
from .infoservant_impl import infoservant
```

### Step 3: Write Tests

Create the `tests/test_infoservant.py` file with some basic tests:

```python
import unittest
from infoservant import infoservant

class Testinfoservant(unittest.TestCase):
    def test_infoservant(self):
        # This is a simple test case. You might want to mock requests for real tests.
        content = infoservant("http://example.com")
        self.assertIn("Example Domain", content)

if __name__ == '__main__':
    unittest.main()
```

### Step 4: Create the README.md

Create a `README.md` file with a description of your package:

````markdown
# infoservant

A simple Python package to extract text content from a webpage.

## Installation

```bash
pip install infoservant
```
````

## Usage

```python
import infoservant

text = infoservant("http://mysite.com")
print(text)
```

````

### Step 5: Create the setup.py

Create a `setup.py` file to define the package metadata and dependencies:

```python
from setuptools import setup, find_packages

setup(
    name="infoservant",
    version="0.1.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="A simple Python package to extract text content from a webpage.",
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url="https://github.com/yourusername/infoservant",
    packages=find_packages(),
    install_requires=[
        "requests",
        "beautifulsoup4"
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)
````

### Step 6: Create the MANIFEST.in

Create a `MANIFEST.in` file to include the README.md in the package:

```
include README.md
```

### Step 7: Build and Upload the Package

1. **Build the package**:

   ```bash
   pip install wheel
   python setup.py sdist bdist_wheel
   ```

2. **Upload the package to PyPI**:
   First, install `twine` if you haven't already:

   ```bash
   pip install twine
   ```

   Then, upload the package:

   ```bash
   twine upload dist/*
   ```

### Step 8: Install and Test the Package

After uploading, you can install your package using pip:

```bash
pip install infoservant
```

And test it with the provided usage example:

```python
import infoservant

text = infoservant("http://example.com")
print(text)
```

That's it! You've now created, packaged, and distributed a Python package on PyPI.

While developing a Python package, it's often useful to be able to invoke it from the command line without having to install it via `pip` every time you make a change. You can achieve this by using the `editable` mode of `pip` or by setting up a virtual environment. Here are the steps to do this:

### Step 1: Create a Virtual Environment

First, create a virtual environment for your project. This helps to isolate your development environment from your system Python installation.

```bash
python -m venv venv
```

Activate the virtual environment:

- On Windows:

  ```bash
  venv\Scripts\activate
  ```

- On macOS and Linux:
  ```bash
  source venv/bin/activate
  ```

### Step 2: Install the Package in Editable Mode

With the virtual environment activated, install your package in editable mode:

```bash
pip install -e .
```

The `-e` flag stands for "editable," which means that changes to your source code will be immediately reflected without needing to reinstall the package.

### Step 3: Create a Command-Line Interface (CLI)

To invoke your package from the command line, you can create a CLI entry point. Modify your `setup.py` to include an `entry_points` section:

```python
from setuptools import setup, find_packages

setup(
    name="infoservant",
    version="0.1.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="A simple Python package to extract text content from a webpage.",
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url="https://github.com/yourusername/infoservant",
    packages=find_packages(),
    install_requires=[
        "requests",
        "beautifulsoup4"
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
    entry_points={
        'console_scripts': [
            'infoservant=infoservant.infoservant:main',
        ],
    },
)
```

### Step 4: Modify Your Code to Support CLI

Update your `infoservant/infoservant.py` to include a `main` function that will be used as the entry point for the CLI:

```python
import requests
from bs4 import BeautifulSoup
import sys

def infoservant(url):
    response = requests.get(url)
    response.raise_for_status()  # Raise an error for bad status codes
    soup = BeautifulSoup(response.text, 'html.parser')
    return soup.get_text()

def main():
    if len(sys.argv) != 2:
        print("Usage: infoservant <URL>")
        sys.exit(1)

    url = sys.argv[1]
    try:
        content = infoservant(url)
        print(content)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
```

### Step 5: Test the CLI

With the package installed in editable mode, you can now invoke it from the command line:

```bash
infoservant http://example.com
```

This should print the text content of the specified webpage.

### Summary

By following these steps, you can develop your package and test it from the command line without needing to reinstall it every time you make a change. The key steps are creating a virtual environment, installing the package in editable mode, and setting up a CLI entry point in your `setup.py`.

### Step 2: Uninstall the Package

Use the `pip uninstall` command followed by the package name to uninstall it:

```bash
pip uninstall infoservant
```
