# preshow_mailer/setup.py

from setuptools import setup, find_packages

setup(
    name='preshow_mailer',
    version='0.1.0',
    # Tells Python to find the 'src' folder and treat it as a package
    packages=find_packages(include=['src', 'src.*']), 
    install_requires=[
        'jinja2',
        'PyYAML',
        'requests',
        'python-dotenv'
    ],
)