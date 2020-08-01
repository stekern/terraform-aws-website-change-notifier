#!/usr/bin/env python
#
# Copyright (C) 2020 Erlend Ekern <dev@ekern.me>
#
# Distributed under terms of the MIT license.

"""

"""

from src import main


def test_scraper_should_return_non_empty_list():
    results = main.scrape(
        "https://www.beatport.com/releases/all?per-page=100",
        "//ul[contains(@class, 'bucket-items') and contains(@class, 'ec-bucket')]/li",
    )
    assert len(results)


def test_massage_should_return_empty_dict():
    element = {"id": "1234", "artist": "Example", "title": "Example"}
    attributes = [
        {
            "name": "artist",
            "patterns": [{"pattern": "Example", "exclude": True}],
        }
    ]
    result = main.massage_obj(element, attributes)
    assert result == {}


def test_massage_should_return_empty_dict_when_empty_id():
    element = {"id": ""}
    attributes = [{"name": "id"}]
    result = main.massage_obj(element, attributes)
    assert result == {}


def test_massage_should_return_empty_dict_when_required_attribute_is_empty():
    element = {"id": "1234", "title": ""}
    attributes = [{"name": "id"}, {"name": "title", "required": True}]
    result = main.massage_obj(element, attributes)
    assert result == {}


def test_massage_should_return_element_with_all_keys():
    element = {"id": "1234", "artist": "Example", "title": "Example"}
    result = main.massage_obj(element)
    assert all(key in result for key in element)


def test_massage_should_join_elements():
    element = {
        "id": "1234",
        "artist": ["Artist 1", "Artist 2"],
        "title": "Example",
    }
    attributes = [
        {
            "name": "artist",
            "separator": ", ",
            "patterns": [{"pattern": "Example", "exclude": True}],
        }
    ]
    result = main.massage_obj(element, attributes)

    assert result.get("artist", "") == "Artist 1, Artist 2"


def test_invalid_scraper_should_be_skipped():
    scraper = {
        "url": "https://www.beatport.com/releases/all?per-page=100",
        "element_xpath": "//ul[contains(@class, 'bucket-items') and contains(@class, 'ec-bucket')]/li",
        "attributes": [
            {
                "name": "title",
                "xpath": ".//p[@class='buk-horz-release-title']/a/text()",
            },
        ],
    }
    result = main.get_valid_scrapers([scraper])
    assert len(result) == 0
