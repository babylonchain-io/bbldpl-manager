import os

from setuptools import setup, find_packages
from subprocess import call

def get_long_desc():
    with open("README.md", "r") as readme:
        desc = readme.read()

    return desc

def setup_package():
    setup(
        name='bbldpl-manager',
        version='0.0.1',
        description='Babylon Deployment Manager',
        long_description=get_long_desc(),
        long_description_content_type="text/markdown",
        url='https://github.com/babylonchain-io/bbldpl-manager',
        packages=find_packages(),
        entry_points = {
            'console_scripts': [
                'bbldpl-manager=bbldpl_manager.__main__:main',
            ],
        },
        classifiers=[
            'Programming Language :: Python :: 3'
            'Intended Audience :: Developers',
            'Intended Audience :: System Administrators',
        ],
        license='MIT',
        author = 'BabylonChain',
        author_email = 'admin@babylonchain.io',
        install_requires=[
            'docker>=5.0.3'
        ],
    )

if __name__ == '__main__':
    setup_package()
