# PROJECT NAME GOES HERE

PROJECT DESCRIPTION GOES HERE

## Getting started

DESCRIBE HOW TO USE THE PROJECT AND HOW TO GET IT RUNNING.

## docs folder

Project docs are in the **`docs/`** folder and are built as a Quarto book,
rendered to HTML. The rendered HTML can be found in the **`docs/_book/`** subfolder.

To rebuild the docs book, run the following from the `docs/` directory:

```bash
quarto render
```

See `docs/documentationGuides/QUARTO-DOC-GUIDE.qmd` for Quarto installation and usage.


It is generally very helpful for AIs to have access to complete up to date 
documentation for the projects they are working on.
This gives the AI the context it needs to make good decisions and navigate the code and other resources
for the project. It is most helpful if the documentation for a project follows standard practices
to allow the AI to understand your project based on other projects that it has seen while the AI 
was being trained. 

To this end, this template puts all documentation in a `docs` subfolder of the main project.
The README.md file in the project's main folder is also commonly used to explain the purpose
and general knowledge needed for working with the project. This README.md file is also
displayed by default on the main page of a github repo. The root README.md is linked into 
the Quarto book inside the index.qmd file.

It is also very helpful for human beings to be able to easily navigate the same documentation
that the AI sees. This template is setup to work with the Quarto documentation system. 
Search online for Quarto for more info about how to use it. Quarto is used to render the 
.qmd files (ie. Quarto extended markdown files) into HTML. 

## Suggestions for using this repo

- **Make sure to ask the AI to update the documentation after the AI changes the repo**.
  It is very important that the documentation is kept up to date along with all changes to the 
  code. Best practice is therefore to have the AI update any documentation that could be affected
  by changes the AI makes. 

- **Ask AI to update automated test cases after every change to the repo**.

