from setuptools import setup, find_packages

setup(
    name="trace-loop-ci",
    version="0.1.0",
    description="TraceLoop CI — pytest plugin for LLM behavioral regression testing",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="TraceLoop CI Contributors",
    url="https://github.com/traceloop-ci/traceloop-ci",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[
        "httpx>=0.28.0",
        "pytest>=7.0",
    ],
    entry_points={
        "pytest11": [
            "trace_loop = trace_loop.plugin",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Testing",
    ],
)
