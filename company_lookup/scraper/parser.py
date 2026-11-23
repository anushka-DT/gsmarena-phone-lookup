from urllib.parse import urljoin

from bs4 import BeautifulSoup


def parse_manufacturers(html: str, base_url: str) -> dict[str, str]:
    """Extract manufacturer names and their listing URLs."""
    soup = BeautifulSoup(html, "html.parser")

    manufacturers: dict[str, str] = {}
    seen_names: set[str] = set()

    for link in soup.select("table td a"):
        name_element = link.find(string=True, recursive=False)
        name = name_element.strip() if name_element else ""
        href = link.get("href")

        if not name or not href:
            continue

        normalized_name = name.casefold()

        if normalized_name in seen_names:
            continue

        manufacturers[name] = urljoin(base_url, href)
        seen_names.add(normalized_name)

    return manufacturers


def parse_phone_links(html: str, base_url: str) -> list[dict[str, str]]:
    """Extract smartphone names and their detail URLs."""
    soup = BeautifulSoup(html, "html.parser")

    phones: list[dict[str, str]] = []
    seen_urls: set[str] = set()

    for item in soup.select("#review-body .makers li"):
        link = item.find("a", href=True)
        image = item.find("img")

        if link is None or image is None:
            continue

        title = image.get("title", "")

        if not isinstance(title, str):
            continue

        if "smartphone" not in title.casefold():
            continue

        name_element = link.select_one("strong span")

        if name_element is None:
            continue

        name = name_element.get_text(" ", strip=True)
        href = link.get("href")

        if not name or not href:
            continue

        detail_url = urljoin(base_url, href)

        if detail_url in seen_urls:
            continue

        phones.append({"name": name, "url": detail_url})
        seen_urls.add(detail_url)

    return phones


def parse_specifications(html: str) -> dict[str, dict[str, list[str]]]:
    """Extract phone specifications while preserving continuation values."""
    soup = BeautifulSoup(html, "html.parser")

    specifications: dict[str, dict[str, list[str]]] = {}

    current_section: str | None = None
    previous_label: str | None = None

    for row in soup.select("#specs-list tr"):
        cells = row.find_all(["th", "td"], recursive=False)

        section_cell = next(
            (cell for cell in cells if cell.name == "th"),
            None,
        )

        if section_cell:
            current_section = section_cell.get_text(" ", strip=True)
            specifications.setdefault(current_section, {})
            previous_label = None

        if current_section is None:
            continue

        label_cell = next(
            (
                cell
                for cell in cells
                if cell.name == "td" and "ttl" in cell.get("class", [])
            ),
            None,
        )

        value_cell = next(
            (
                cell
                for cell in cells
                if cell.name == "td" and "nfo" in cell.get("class", [])
            ),
            None,
        )

        if value_cell is None:
            continue

        value = value_cell.get_text(" ", strip=True)

        if not value:
            continue

        label = label_cell.get_text(" ", strip=True) if label_cell else ""

        data_spec = value_cell.get("data-spec")
        is_optional = row.has_attr("data-spec-optional")

        section_specs = specifications[current_section]

        if label:
            key = label
            previous_label = key
        elif data_spec:
            key = str(data_spec)
            previous_label = None
        elif is_optional and previous_label:
            key = previous_label
        else:
            key = "Unlabeled"
            previous_label = None

        section_specs.setdefault(key, []).append(value)

    return specifications


def get_next_page_url(html: str, current_url: str) -> str | None:
    """Extract the next manufacturer listing page URL."""
    soup = BeautifulSoup(html, "html.parser")

    next_link = soup.select_one('a.prevnextbutton[title="Next page"]')

    if next_link is None:
        return None

    href = next_link.get("href")

    if not isinstance(href, str) or not href.strip():
        return None

    return urljoin(current_url, href)
