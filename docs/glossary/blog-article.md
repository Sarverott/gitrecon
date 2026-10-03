# Blog article

> An article of a blog, captured as markdown with checksums.

## What it is

Article links are read from the blog's index page (same site, `.html`); each article is converted with markdownify. Pages also reveal the feeds they advertise (`<link rel="alternate">`).

## Where

`gitrecon.sources.blog`, `gitrecon.models.BlogArticle`. CLI: `gitrecon blog [URL] --dump --save` (default: blog.apokryf.pl).

## Relations

Discovered feeds become [[news-feed]]s. Ported from a [[gist]] notebook.
