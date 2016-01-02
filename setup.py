from setuptools import setup, find_packages

setup(
    name="celobox",
    version="0.1a",
    packages=find_packages(),
    install_requires=[
        'selenium',
        'requests',
        'enum34',
        'pyyaml',
    ],
    entry_points={
        'console_scripts': [
            'phantompasswd = celobox.phantompasswd:main'
        ]
    },
    package_data={
        'celobox': ['manifests/*']
    }
)
