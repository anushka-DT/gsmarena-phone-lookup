from company_lookup import GSMArenaScraper


def test_parse_named_specifications():
    html = """
    <table id="specs-list">
        <tr><th>Network</th></tr>
        <tr>
            <td class="ttl">Technology</td>
            <td class="nfo">GSM / HSPA / LTE / 5G</td>
        </tr>
    </table>
    """

    result = GSMArenaScraper.parse_specifications(html)

    assert result == {"Network": {"Technology": ["GSM / HSPA / LTE / 5G"]}}


def test_parse_optional_continuation_rows():
    html = """
    <table id="specs-list">
        <tr><th>Network</th></tr>
        <tr>
            <td class="ttl">Technology</td>
            <td class="nfo">GSM / HSPA</td>
        </tr>
        <tr data-spec-optional>
            <td class="nfo">LTE</td>
        </tr>
    </table>
    """

    result = GSMArenaScraper.parse_specifications(html)

    assert result["Network"]["Technology"] == ["GSM / HSPA", "LTE"]


def test_parse_independent_unlabeled_specification():
    html = """
    <table id="specs-list">
        <tr><th>Body</th></tr>
        <tr>
            <td class="nfo" data-spec="bodyother">
                IP68 dust/water resistant
            </td>
        </tr>
    </table>
    """

    result = GSMArenaScraper.parse_specifications(html)

    assert result["Body"]["bodyother"] == ["IP68 dust/water resistant"]


def test_parse_unlabeled_row_without_metadata():
    html = """
    <table id="specs-list">
        <tr><th>Body</th></tr>
        <tr><td class="nfo">Some specification</td></tr>
    </table>
    """

    result = GSMArenaScraper.parse_specifications(html)

    assert result["Body"]["Unlabeled"] == ["Some specification"]


def test_parse_multiple_sections():
    html = """
    <table id="specs-list">
        <tr><th>Network</th></tr>
        <tr>
            <td class="ttl">Technology</td>
            <td class="nfo">5G</td>
        </tr>
        <tr><th>Display</th></tr>
        <tr>
            <td class="ttl">Type</td>
            <td class="nfo">AMOLED</td>
        </tr>
    </table>
    """

    result = GSMArenaScraper.parse_specifications(html)

    assert result["Network"]["Technology"] == ["5G"]
    assert result["Display"]["Type"] == ["AMOLED"]


def test_parse_phone_links():
    html = """
    <div id="review-body" class="section-body">
        <div class="makers">
            <ul>
                <li>
                    <a href="samsung_galaxy_s24_ultra-12771.php">
                        <img title="Samsung Galaxy S24 Ultra Android smartphone.">
                        <strong><span>Galaxy S24 Ultra</span></strong>
                    </a>
                </li>
                <li>
                    <a href="apple_iphone_15_pro_max-12548.php">
                        <img title="Apple iPhone 15 Pro Max iOS smartphone.">
                        <strong><span>iPhone 15 Pro Max</span></strong>
                    </a>
                </li>
            </ul>
        </div>
    </div>
    """

    result = GSMArenaScraper.parse_phone_links(html)

    assert result == [
        {
            "name": "Galaxy S24 Ultra",
            "url": "https://www.gsmarena.com/samsung_galaxy_s24_ultra-12771.php",
        },
        {
            "name": "iPhone 15 Pro Max",
            "url": "https://www.gsmarena.com/apple_iphone_15_pro_max-12548.php",
        },
    ]


def test_parse_phone_links_excludes_tablets_and_watches():
    html = """
    <div id="review-body">
        <div class="makers">
            <ul>
                <li>
                    <a href="samsung_phone-1.php">
                        <img title="Samsung Android smartphone.">
                        <strong><span>Galaxy Phone</span></strong>
                    </a>
                </li>
                <li>
                    <a href="samsung_tablet-2.php">
                        <img title="Samsung Android tablet.">
                        <strong><span>Galaxy Tab</span></strong>
                    </a>
                </li>
                <li>
                    <a href="samsung_watch-3.php">
                        <img title="Samsung Android watch.">
                        <strong><span>Galaxy Watch</span></strong>
                    </a>
                </li>
            </ul>
        </div>
    </div>
    """

    result = GSMArenaScraper.parse_phone_links(html)

    assert result == [
        {
            "name": "Galaxy Phone",
            "url": "https://www.gsmarena.com/samsung_phone-1.php",
        }
    ]


def test_parse_phone_links_ignores_invalid_entries():
    html = """
    <div id="review-body">
        <div class="makers">
            <ul>
                <li>
                    <a href="valid_phone.php">
                        <img title="Android smartphone.">
                        <strong><span>Valid Phone</span></strong>
                    </a>
                </li>
                <li>
                    <a href="missing_image.php">
                        <strong><span>Missing Image</span></strong>
                    </a>
                </li>
                <li>
                    <a href="missing_name.php">
                        <img title="Android smartphone.">
                    </a>
                </li>
                <li>
                    <a>
                        <img title="Android smartphone.">
                        <strong><span>Missing URL</span></strong>
                    </a>
                </li>
                <li>
                    <a href="missing_title.php">
                        <img>
                        <strong><span>Missing Title</span></strong>
                    </a>
                </li>
            </ul>
        </div>
    </div>
    """

    result = GSMArenaScraper.parse_phone_links(html)

    assert result == [
        {
            "name": "Valid Phone",
            "url": "https://www.gsmarena.com/valid_phone.php",
        }
    ]


def test_parse_phone_links_removes_duplicate_urls():
    html = """
    <div id="review-body">
        <div class="makers">
            <ul>
                <li>
                    <a href="samsung_phone-1.php">
                        <img title="Samsung Android smartphone.">
                        <strong><span>Galaxy Phone</span></strong>
                    </a>
                </li>
                <li>
                    <a href="samsung_phone-1.php">
                        <img title="Samsung Android smartphone.">
                        <strong><span>Galaxy Phone Duplicate</span></strong>
                    </a>
                </li>
            </ul>
        </div>
    </div>
    """

    result = GSMArenaScraper.parse_phone_links(html)

    assert len(result) == 1
    assert result[0]["name"] == "Galaxy Phone"
    assert result[0]["url"] == "https://www.gsmarena.com/samsung_phone-1.php"


def test_get_next_page_url():
    html = """
    <a href="samsung-phones-f-9-0-p3.php"
       class="prevnextbutton"
       title="Next page">►</a>
    """

    result = GSMArenaScraper.get_next_page_url(
        html,
        "https://www.gsmarena.com/samsung-phones-9.php",
    )

    assert result == "https://www.gsmarena.com/samsung-phones-f-9-0-p3.php"


def test_get_next_page_url_returns_none_on_last_page():
    html = """
    <div class="makers">
        <ul>
            <li>Phone listing</li>
        </ul>
    </div>
    """

    result = GSMArenaScraper.get_next_page_url(
        html,
        "https://www.gsmarena.com/samsung-phones-f-9-0-p3.php",
    )

    assert result is None


def test_get_next_page_url_ignores_empty_href():
    html = """
    <a href=""
       class="prevnextbutton"
       title="Next page">►</a>
    """

    result = GSMArenaScraper.get_next_page_url(
        html,
        "https://www.gsmarena.com/samsung-phones-9.php",
    )

    assert result is None
