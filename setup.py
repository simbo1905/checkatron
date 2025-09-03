from setuptools import setup, find_packages

setup(
    name="checkatron",
    version="0.1.0",
    description="SQL diff generation tool for database table comparisons",
    author="Your Name",
    packages=find_packages(),
    install_requires=[
        "jinja2>=3.1",
        "pytest>=7.4",
        "duckdb>=0.9",
    ],
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "checkatron=checkatron.diffgen:main",
        ],
    },
)
