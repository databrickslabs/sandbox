from setuptools import setup, find_packages

setup(
    name="sql_migration_assistant",
    version="0.1",
    packages=find_packages(where="src"),  # Specify src as the package directory
    package_dir={"": "src"},
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.10',
)