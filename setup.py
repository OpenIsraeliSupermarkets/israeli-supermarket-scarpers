from io import open
from setuptools import setup

with open("README.md", encoding="utf-8") as f:
    long_description = "\n" + f.read()

with open("requirements.txt", encoding="utf-8") as f:
    required = f.read().splitlines()

with open("requirements-dev.txt", encoding="utf-8") as f:
    dev_required = f.read().splitlines()

setup(
    # Needed to silence warnings (and to be a worthwhile package)
    name="il-supermarket-scraper",
    url="https://github.com/jladan/package_demo",
    author="Sefi Erlich",
    author_email="erlichsefi@gmail.com",
    # Needed to actually package something
    packages=[
        "il_supermarket_scarper",
        "il_supermarket_scarper.engines",
        "il_supermarket_scarper.scrappers",
        "il_supermarket_scarper.utils",
    ],
    # Needed for dependencies
    install_requires=required,
    tests_require=dev_required,
    extras_require={"test": ["pytest"]},
    # *strongly* suggested for sharing
    version="0.4.0",
    # The license can be anything you like
    license="MIT",
    description="python package that implement a scraping for israeli supermarket data",
    # We will also need a readme eventually (there will be a warning)
    long_description=long_description,
    long_description_content_type="text/markdown",
    keywords=["israel", "israeli", "scraper", "supermarket"],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Build Tools",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
    ],
)
