from setuptools import setup, find_packages

# Read the requirements.txt file
def load_requirements(filename="requirements.txt"):
    with open(filename, "r") as file:
        return file.read().splitlines()

setup(
    name="sql_migration_assistant",
    version="0.1",
    packages=find_packages(where="src"),  # Specify src as the package directory
    package_dir={"": "src"},
    include_package_data=True,  # Include files specified in MANIFEST.in
    package_data={
        'sql_migration_assistant': ['config.yml'],  # Include YAML file
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    install_requires=load_requirements(),
    python_requires='>=3.10',
)