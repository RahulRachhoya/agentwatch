from setuptools import setup, find_packages

setup(
    name="agentwatch",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "httpx>=0.20.0",
    ],
)
