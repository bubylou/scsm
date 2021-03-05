from setuptools import setup, find_packages
import scsm

with open('README.md', 'r') as f:
    README = f.read()

setup(
    name=scsm.__title__,
    version=scsm.__version__,
    url=scsm.__url__,
    description=scsm.__summary__,
    long_description=README,
    long_description_content_type='text/markdown',
    license=scsm.__license__,
    author=scsm.__author__,
    author_email=scsm.__email__,
    packages=find_packages(exclude=['tests']),
    python_requires='>= 3.6',
    install_requires=[
        'click >= 6.6',
        'libtmux >= 0.8.5',
        'ruamel.yaml >= 0.15.75',
        'vdf >= 2.4'
    ],
    include_package_data=True,
    entry_points={
        "console_scripts": ['scsm=scsm.cli:main']
        },
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Natural Language :: English',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: POSIX :: Linux',
        'Operating System :: Microsoft :: Windows',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Topic :: Utilities'
    ],
)
