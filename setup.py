from setuptools import setup

setup(
    # Needed to silence warnings (and to be a worthwhile package)
    name="il-supermarket-scraper",
    url="https://github.com/jladan/package_demo",
    author="Sefi Erlich",
    author_email="erlichsefi@gmail.com",
    # Needed to actually package something
    packages=[
        "il_supermarket_scarper",
    ],
    # Needed for dependencies
    install_requires=[
        "retry==0.9.2",
        "mock==4.0.3",
        "requests==2.27.1",
        "lxml==4.9.1",
        "beautifulsoup4==4.10.0",
        "pymongo==4.2.0",
        "pytz==2022.4",
    ],
    tests_require=["pytest==7.1"],
    extras_require={"test": ["pytest"]},
    # *strongly* suggested for sharing
    version="0.1",
    # The license can be anything you like
    license="MIT",
    description="An example of a python package from pre-existing code",
    # We will also need a readme eventually (there will be a warning)
    # long_description=open('README.md').read(),
    keywords = ['israel', 'israeli', 'scraper','supermarket'], 
    classifiers=[
    'Development Status :: 3 - Alpha',      # Chose either "3 - Alpha", "4 - Beta" or "5 - Production/Stable" as the current state of your package
    'Intended Audience :: Developers',      # Define that your audience are developers
    'Topic :: Software Development :: Build Tools',
    'License :: OSI Approved :: MIT License',   # Again, pick a license
    'Programming Language :: Python :: 3',      #Specify which pyhton versions that you want to support
    'Programming Language :: Python :: 3.4',
    'Programming Language :: Python :: 3.5',
    'Programming Language :: Python :: 3.6',
  ],
)
