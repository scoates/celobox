from setuptools import setup

setup(
    name="celobox",
    version="0.1a",
    packages=['celobox'],
    install_requires=[
        'selenium',
        'requests',
        'enum34',
        'pyyaml',
    ],
    entry_points={
        'console_scripts': [
            'celobox = celobox.phantompasswd:main'
        ]
    },
    package_data={
        'celobox': ['manifests/*']
    }
)
