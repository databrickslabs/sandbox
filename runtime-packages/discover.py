# Databricks notebook source

import pkg_resources, json, sys, platform, subprocess
from pyspark.version import __version__

jars = []
for j in subprocess.check_output(['ls', '-1', '/databricks/jars']).decode().split("\n"):
    if '--mvn--' in j or '--maven-trees--' in j:
        split = j.split('--')[-1][:-4].split('__')
        if not len(split) == 3:
            continue
        group, artifactId, version = split
        jars.append({
            'group': group,
            'name': artifactId,
            'version': version,
        })
jars = sorted(jars, key=lambda jar: (jar['group'], jar['name']))

python_packages = [
    {"name": n, "version": v}
    for n, v in sorted([(i.key, i.version) 
    for i in pkg_resources.working_set])]
python_packages = sorted(python_packages, key=lambda x: x['name'])

runtime = dbutils.widgets.get("runtime")
dbutils.notebook.exit(json.dumps({
    'name': runtime,
    'spark_version': __version__[0:5],
    'python_version': platform.python_version(),
    'pypi': python_packages,
    'jars': jars,
}))