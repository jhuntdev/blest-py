from setuptools import setup

with open("README.md", encoding="utf-8") as readme_file:
    readme = readme_file.read()

setup(
    name="blest",
    version="0.1.1",
    author="JHunt",
    author_email="blest@jhunt.dev",
    description="The Python reference implementation of BLEST (Batch-able, Lightweight, Encrypted State Transfer), an improved communication protocol for web APIs which leverages JSON, supports request batching and selective returns, and provides a modern alternative to REST.",
    long_description=readme,
    long_description_content_type="text/markdown",
    url="https://blest.jhunt.dev",
    packages=["."],
    classifiers=[
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    install_requires=[
        "aiohttp"
    ],
    python_requires=">=3.8",
    platforms="any",
)
