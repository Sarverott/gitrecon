---
name: Teach gitrecon something
about: A language, framework, tool, import style or commit type it does not recognise yet
title: ''
labels: enhancement
assignees: ''

---

Most of what gitrecon recognises is data in `resources/`, so this is often a few lines - a pull
request is welcome too (guide: "Analysing code" > "Teaching it more").

**What is not recognised**
[a language / a framework or tool / how a language imports files / a commit type / requirement keywords / other]

**How it can be recognised**
 - language: file extensions or file names, and how its comments and strings look
 - framework or tool: the package name and its ecosystem (npm, PyPI, Composer, Cargo, Go, gems), or a file that gives it away
 - imports: an example line, and which file it points to

**A public example**
A repository (or a few lines of a file) where it shows.

**What gitrecon says today**
The output of `gitrecon analyze PATH` or `gitrecon imports PATH` on it, if you have it.
