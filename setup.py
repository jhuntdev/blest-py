from setuptools import setup, find_packages

with open("README.md", encoding="utf-8") as readme_file:
    readme = readme_file.read()

setup(
    name="BLEST",
    version="0.0.4",
    author="JHunt",
    author_email="blest@jhunt.dev",
    description="The Python reference implementation of BLEST (Batch-able, Lightweight, Encrypted State Transfer)",
    long_description=readme,
    long_description_content_type="text/markdown",
    url="https://github.com/jhuntdev/blest-py",
    packages=find_packages(),
    classifiers=[
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    install_requires=[
        "asyncio",
        "aiohttp",
        "json",
        "copy",
        "os"
    ],
    python_requires=">=3.6",
    platforms="any",
)
