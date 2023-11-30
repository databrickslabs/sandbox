# Adding new experiments

1. Create a new folder in the root of the repository.
2. Add your and your team GitHub handles into the [`CODEOWNERS`](./CODEOWNERS) file. See [documentation](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners#codeowners-file-location). Please keep the list of folder sorted alphabetically.
3. Create a `README.md` file in the root of your folder and add frontmatter metadata on top of it. Please keep `Your awesome project title` under 55-60 characters. There'll be linting ruled added automatically.

```
---
title: "Your awesome project title"
language: python
author: "Your Name"
date: 2022-10-15

tags: 
- list
- of
- awesome
- tags
---

# Your awesome project title

... markdown documentation about your project. People will be reading it.
```

4. Create a branch and push it to this repository either with a fork (if you're not added directly) and create a pull request. Reviewers will be automatically assigned.

# Python projects

..

# Go projects

We use [mutliple modules](https://github.com/golang/tools/blob/master/gopls/doc/workspace.md#multiple-modules) setup for go-based tools and libraries.

To debug in VSCode, create `.vscode/launch.json` with approximately the following contents:

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "metascan clone-all",
            "type": "go",
            "request": "launch",
            "mode": "debug",
            "program": "${workspaceFolder}/metascan/main.go",
            "args": [
                "clone-all",
                "--debug"
            ]
        }
    ]
}
```