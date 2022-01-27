from pathlib import Path
from setuptools import setup, find_packages  # type: ignore[import]

long_description = Path("README.md").read_text()
reqs = Path("requirements.txt").read_text().strip().splitlines()

pkg = "malexport"
setup(
    name=pkg,
    version="0.1.0",
    url="https://github.com/seanbreckenridge/malexport",
    author="Sean Breckenridge",
    author_email="seanbrecke@gmail.com",
    description=("""backs up info from your MAL account"""),
    long_description=long_description,
    long_description_content_type="text/markdown",
    license="MIT",
    packages=find_packages(),
    install_requires=reqs,
    package_data={pkg: ["py.typed"]},
    zip_safe=False,
    keywords="",
    entry_points={"console_scripts": ["malexport = malexport.__main__:main"]},
    extras_require={
        "testing": [
            "mypy",
        ]
    },
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
)
