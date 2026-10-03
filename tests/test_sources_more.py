"""RFC index, RSS/Atom/RDF feeds and blog harvesting (all offline)."""

from datetime import datetime, timezone

import pytest
from conftest import FIXTURES, FakeResponse, FakeSession

from gitrecon.models.feed_item import FeedItem
from gitrecon.sources import blog, rfc_index
from gitrecon.sources.feeds import FeedReader, parse_date, parse_feed

# --- RFC index ---------------------------------------------------------------


@pytest.fixture(scope="module")
def rfcs():
    text = (FIXTURES / "rfc-index-sample.txt").read_text(encoding="utf-8")
    return {rfc.number: rfc for rfc in rfc_index.parse_index(text)}


def test_rfc_index_skips_preamble_and_reads_all_entries(rfcs):
    assert sorted(rfcs) == [1, 3, 14, 2026, 9999, 10041, 10042]


def test_rfc_basic_fields(rfcs):
    first = rfcs[1]
    assert (first.title, first.authors, first.date) == ("Host Software", ["S. Crocker"], "April 1969")
    assert first.status == "UNKNOWN" and first.doi == "10.17487/RFC1" and first.formats == ["txt", "html"]
    assert first.key == "rfc:RFC1"


def test_rfc_relations_and_multiword_status(rfcs):
    process = rfcs[2026]
    assert process.status == "BEST CURRENT PRACTICE"
    assert process.obsoletes == ["RFC1602", "RFC1871"]
    assert "RFC9282" in process.updated_by and process.also == ["BCP9"]
    assert rfcs[3].obsoleted_by == ["RFC10"]


def test_rfc_five_digit_numbers_and_wrapped_words(rfcs):
    ospf = rfcs[10041]
    assert ospf.status == "PROPOSED STANDARD"  # wrapped over two lines
    assert ospf.doi == "10.17487/RFC10041"
    assert ospf.updates == ["RFC5443", "RFC6987", "RFC8379", "RFC8770"]
    assert "Module-Lattice-Based" in rfcs[10042].title  # "Module-\n     Lattice" joined


def test_rfc_not_issued(rfcs):
    assert rfcs[14].not_issued and rfcs[14].title == "Not Issued"


def test_rfc_title_with_parentheses_and_editors():
    entry = (
        "10002 Certificate Management over CMS (CMC). J. Mandel, Ed., S. Turner,\n"
        "     Ed.. July 2026. (Format: HTML, TXT) (Status: PROPOSED STANDARD) (DOI:\n"
        "     10.17487/RFC10002)\n"
    )
    rfc = rfc_index.parse_entry(entry)
    assert rfc.title == "Certificate Management over CMS (CMC)"
    assert rfc.authors == ["J. Mandel, Ed.", "S. Turner, Ed."]
    assert rfc.date == "July 2026"


# --- feeds -------------------------------------------------------------------


def test_parse_rss():
    feed = parse_feed((FIXTURES / "feed-rss.xml").read_bytes(), "https://www.exploit-db.com/rss.xml")
    assert (feed.format, feed.title, len(feed.items)) == ("rss", "Exploit Database", 2)
    item = feed.items[0]
    assert item.published == datetime(2026, 10, 1, tzinfo=timezone.utc)
    assert item.summary == "Command injection"  # HTML stripped
    assert item.authors == ["someone"] and item.categories == ["remote"]
    assert feed.items[1].id == "https://example.com/2"  # link stands in for a missing guid


def test_parse_atom():
    feed = parse_feed((FIXTURES / "feed-atom.xml").read_bytes())
    item = feed.items[0]
    assert feed.format == "atom"
    assert item.link == "https://github.com/advisories/GHSA-xmhj-hj4f-c924"
    assert item.categories == ["PIP"] and item.authors == ["GitHub"]
    assert item.updated.second == 17 and item.summary == "Malicious package"


def test_parse_rdf():
    feed = parse_feed((FIXTURES / "feed-rdf.xml").read_bytes())
    item = feed.items[0]
    assert (feed.format, feed.title, item.id) == ("rdf", "RDF Example", "https://example.org/a")
    assert item.published.utcoffset().total_seconds() == 7200
    assert item.categories == ["ietf"]


def test_parse_feed_rejects_entity_bombs_and_non_feeds():
    bomb = b'<?xml version="1.0"?><!DOCTYPE r [<!ENTITY a "aaaa"><!ENTITY b "&a;&a;">]><rss>&b;</rss>'
    with pytest.raises(Exception):
        parse_feed(bomb)
    with pytest.raises(ValueError):
        parse_feed(b"<html><body/></html>")


def test_parse_date_forms():
    assert parse_date("2026-10-03T00:31:16Z").tzinfo is not None
    assert parse_date("Thu, 01 Oct 2026 00:00:00 GMT").year == 2026
    assert parse_date("not a date") is None


def test_feed_reader_conditional_requests_and_dedup(tmp_path):
    url = "https://www.exploit-db.com/rss.xml"
    first = FakeResponse(None, headers={"ETag": '"v1"'})
    first.content = (FIXTURES / "feed-rss.xml").read_bytes()
    session = FakeSession({url: [first, FakeResponse(None, status=304)]})
    reader = FeedReader(state_file=tmp_path / "feeds.json", session=session)

    assert len(reader.poll(url)) == 2
    assert reader.poll(url) == []  # 304
    assert session.calls[1][2]["headers"]["If-None-Match"] == '"v1"'

    again = FeedReader(state_file=tmp_path / "feeds.json", session=FakeSession({url: [first]}))
    assert again.poll(url) == []  # same items, already seen (state reloaded from disk)


def test_feed_item_record_roundtrip():
    item = parse_feed((FIXTURES / "feed-atom.xml").read_bytes(), "u").items[0]
    assert FeedItem.from_record(item.to_record()).to_record() == item.to_record()


# --- blog --------------------------------------------------------------------

BLOG_INDEX = """<html><head>
<link rel="alternate" type="application/atom+xml" href="https://blog.apokryf.pl/feeds/posts/default"/>
<link rel="stylesheet" href="/style.css"/>
</head><body>
<a href="https://blog.apokryf.pl/2026/03/report-emergent-collective-narrative.html">a</a>
<a href="/2026/03/notation-of-new-scales.html#comments">b</a>
<a href="https://blog.apokryf.pl/2026/03/notation-of-new-scales.html">b again</a>
<a href="https://elsewhere.example/x.html">foreign</a>
<a href="#top">top</a>
</body></html>"""


def test_blog_article_links_and_feeds():
    base = "https://blog.apokryf.pl"
    assert blog.article_links(BLOG_INDEX, base) == [
        "https://blog.apokryf.pl/2026/03/notation-of-new-scales.html",
        "https://blog.apokryf.pl/2026/03/report-emergent-collective-narrative.html",
    ]
    assert blog.discover_feeds(BLOG_INDEX, base) == ["https://blog.apokryf.pl/feeds/posts/default"]


def test_blog_article_markdown_and_checksums():
    url = "https://blog.apokryf.pl/2026/03/report-emergent-collective-narrative.html"
    article = blog.html_to_article(url, "<h1>Report</h1><p>Some <b>bold</b> text</p>")
    assert article.name == "REPORT EMERGENT COLLECTIVE NARRATIVE"
    assert "**bold**" in article.markdown
    dump = article.to_markdown()
    assert dump.startswith(f"- {article.url_checksum} - {article.name_checksum}\n### ARTICLE FROM [REPORT")
    assert dump.endswith("###### END")
