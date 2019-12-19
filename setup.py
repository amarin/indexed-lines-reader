from glob import glob
from os.path import basename
from os.path import dirname
from os.path import join
from os.path import realpath
from os.path import splitext

from setuptools import find_packages
from setuptools import setup

here = realpath(dirname(__file__))

with open(join(here, 'README.rst'), 'r') as readme_fh:
    README = readme_fh.read()

dist = setup(
    python_requires='>3.6.0',
    name="indexed_lines_reader",
    version="0.1.0",
    license="MIT",
    author="Aleksey Marin",
    author_email="asmadews@gmail.com",
    url="",
    description="Indexed text file lines access enabler",
    long_description=README,
    long_description_content_type='text/x-rst',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    py_modules=[splitext(basename(path))[0] for path in glob('src/*.py')],
    include_package_data=True,
    zip_safe=False,
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "Intended Audience :: Information Technology",
        "License :: OSI Approved :: MIT License",
        "Operating System :: MacOS",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
    ],
    setup_requires=[],
    tests_require=[
        'pytest-runner',
        'pytest>=3.0.6',
        'tox'
    ],
)
