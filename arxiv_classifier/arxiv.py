"""Everything that talks to arXiv: fetching recent papers and parsing the Atom feed."""

import xml.etree.ElementTree as ET

import httpx

from arxiv_classifier.config import settings

API_URL = "https://export.arxiv.org/api/query"
NS = {"a": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}

# The label set: 12 computer-science categories. Descriptions are the "class definitions" both judges read.
CATEGORIES = {
    "cs.AI": "Artificial intelligence: reasoning, planning, knowledge representation, agents, general AI methods",
    "cs.CL": "Computation and language: natural language processing, language models, speech and text",
    "cs.CV": "Computer vision: images, video, 3D vision, visual generation and recognition",
    "cs.LG": "Machine learning: learning algorithms, theory, optimization, representation learning",
    "cs.RO": "Robotics: robot control, manipulation, locomotion, autonomous vehicles",
    "cs.CR": "Cryptography and security: attacks, defenses, privacy, cryptographic protocols",
    "cs.SE": "Software engineering: programming tools, testing, code generation, maintenance",
    "cs.IR": "Information retrieval: search, ranking, recommender systems",
    "cs.HC": "Human-computer interaction: user studies, interfaces, people using technology",
    "cs.DC": "Distributed, parallel and cluster computing: systems, scheduling, large-scale training infrastructure",
    "cs.NI": "Networking and internet architecture: protocols, wireless networks, network systems",
    "cs.DB": "Databases: data management, query processing, data systems",
}


def client() -> httpx.AsyncClient:
    return httpx.AsyncClient(headers={"User-Agent": settings.user_agent}, timeout=60)


def parse(xml: str) -> list[dict]:
    """Atom feed -> one dict per paper, keeping only papers whose primary category is in our label set."""
    papers = []
    for e in ET.fromstring(xml).findall("a:entry", NS):
        primary = e.find("arxiv:primary_category", NS).get("term")
        if primary not in CATEGORIES:
            continue
        url = e.findtext("a:id", namespaces=NS).strip()
        clean = lambda s: " ".join((s or "").split())  # arXiv wraps titles and abstracts with hard newlines
        papers.append({
            "id": url.rsplit("/abs/", 1)[1].split("v")[0],  # 2610.06851v1 -> 2610.06851
            "url": url,
            "title": clean(e.findtext("a:title", namespaces=NS)),
            "abstract": clean(e.findtext("a:summary", namespaces=NS)),
            "authors": ", ".join(a.findtext("a:name", namespaces=NS) for a in e.findall("a:author", NS)),
            "primary_category": primary,
            "categories": [c.get("term") for c in e.findall("a:category", NS)],
            "published": e.findtext("a:published", namespaces=NS),
        })
    return papers


async def recent(http: httpx.AsyncClient, start: int = 0, count: int = 100) -> list[dict]:
    """The newest submissions in our categories. arXiv asks for at most one request every 3 seconds."""
    query = " OR ".join(f"cat:{c}" for c in CATEGORIES)
    r = await http.get(API_URL, params={
        "search_query": query, "sortBy": "submittedDate", "sortOrder": "descending",
        "start": start, "max_results": count})
    r.raise_for_status()
    return parse(r.text)


if __name__ == "__main__":  # self-check for the parser
    sample = """<feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
      <entry><id>http://arxiv.org/abs/2610.06851v1</id><title>Base Models Can
        Reason</title><summary>  We study
        token cues. </summary><published>2026-10-05T17:59:52Z</published>
        <author><name>A. B</name></author><author><name>C. D</name></author>
        <category term="cs.LG"/><category term="cs.CL"/><arxiv:primary_category term="cs.LG"/></entry>
      <entry><id>http://arxiv.org/abs/2610.00001v2</id><title>Off topic</title><summary>x</summary>
        <published>2026-10-05T00:00:00Z</published><category term="math.AG"/><arxiv:primary_category term="math.AG"/></entry>
    </feed>"""
    out = parse(sample)
    assert len(out) == 1, out
    p = out[0]
    assert (p["id"], p["title"], p["abstract"]) == ("2610.06851", "Base Models Can Reason", "We study token cues."), p
    assert p["categories"] == ["cs.LG", "cs.CL"] and p["authors"] == "A. B, C. D", p
    print("arxiv.py ok")
