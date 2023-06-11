from setuptools import setup, find_packages

setup(
    name="blest-py",
    version="0.0.1",
    author="JHunt",
    author_email="blest@jhunt.dev",
    description="The Python reference implementation of BLEST (Batch-able, Lightweight, Encrypted State Transfer)",
    long_description="The Python reference implementation of BLEST (Batch-able, Lightweight, Encrypted State Transfer), an improved communication protocol for web APIs which leverages JSON, supports request batching and selective returns, and provides a modern alternative to REST.",
    long_description_content_type="text/markdown",
    url="https://github.com/jhuntdev/blest-py",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    install_requires=[
        "asyncio",
    ],
    python_requires=">=3.6",
)
