#!/usr/bin/env python
#
# Copyright (C) 2020 Erlend Ekern <dev@ekern.me>
#
# Distributed under terms of the MIT license.

"""

"""

import logging
import os
import random

import boto3
import requests

from concurrent.futures import ThreadPoolExecutor as PoolExecutor
from datetime import datetime
from lxml import etree, html
from timeit import default_timer as timer

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def scrape(url, element_xpath, parse_fn=None):
    """Scrape a website, find elements based on an XPath and (optionally) parse each element"""
    start = timer()
    response = requests.get(url)
    root = html.fromstring(response.content)
    elements = root.xpath(element_xpath)
    if parse_fn:
        elements = [parse_fn(element) for element in elements]
    end = timer()
    logger.info("Took %s seconds to scrape '%s'", end - start, url)
    return elements


def filter_fn(value, attribute):
    """Check if an attribute value is valid based on inclusion and/or exclusion patterns"""
    return all(
        [
            (pattern.get("exclude", False) and pattern["pattern"] not in value)
            or (
                not pattern.get("exclude", False)
                and pattern["pattern"] in value
            )
            for pattern in attribute.get("patterns", [])
        ]
    )


def massage_obj(obj, attributes=[]):
    """Convert a parsed element, or return an empty dict if one or more attributes do not match the supplied patterns (i.e., exclude the current element)"""
    new = {}
    for key, val in obj.items():
        attribute = next((a for a in attributes if a["name"] == key), {})
        separator = attribute.get("separator", " ")
        if type(val) == list:
            new_val = separator.join(str(v) for v in val)
            if not all(filter_fn(str(v), attribute) for v in val):
                logger.warn(
                    "One or more values '%s' did not satisfy attribute pattern(s)",
                    val,
                )
                return {}
            elif attribute.get("required", False) and not len(val):
                logger.warn(
                    "Attribute '%s' required a non-empty value, but value was an empty list",
                    key,
                )
                return {}

        else:
            new_val = str(val)
            if not filter_fn(new_val, attribute):
                logger.warn(
                    "Value '%s' did not match satisfy pattern(s)", new_val
                )
                return {}
            elif attribute.get("required", False) and val == "":
                logger.warn(
                    "Attribute '%s' required a non-empty value, but value was an empty string",
                    key,
                )
                return {}
        new[key] = new_val
    if not new["id"]:
        logger.warn(
            "Attribute 'id' required a non-empty value, but value was '%s'",
            new["id"],
        )
        return {}
    return new


def get_email_body(scraper_results, element_limit=10):
    """Return an email body containing the scraped elements"""
    messages = []
    for scraper in scraper_results:
        if len(scraper["new_elements"]) > 0:
            message = f"Found {len(scraper['new_elements'])} new elements at {scraper['url']}!\n"
            if scraper.get("email_format", None):
                format_fn = lambda element: "".join(
                    f if isinstance(f, str) else element[f["name"]]
                    for f in scraper["email_format"]
                )
            else:
                format_fn = lambda element: " - ".join(
                    v for k, v in element.items()
                )
            message += "\n".join(
                format_fn(element)
                for element in scraper["new_elements"][:element_limit]
            )
            messages.append(message)

    return "\n\n".join(messages)


def get_elements(scraper):
    """Return the elements found using a scraper, or an empty list if
    the number of elements is less or more than expected"""
    max_num_elements = scraper.get("max_num_elements", None)
    min_num_elements = scraper.get("min_num_elements", None)
    element_parser = lambda element: {
        attribute["name"]: element.xpath(attribute["xpath"])
        for attribute in scraper["attributes"]
    }
    elements = scrape(
        scraper["url"], scraper["element_xpath"], parse_fn=element_parser
    )
    elements = [
        massage_obj(element, attributes=scraper["attributes"])
        for element in elements
    ]
    elements = [element for element in elements if element]
    logger.info(
        "Found %s elements at url '%s' %s",
        len(elements),
        scraper["url"],
        elements,
    )
    if min_num_elements is not None and len(elements) < min_num_elements:
        logger.warn(
            "Number of elements %s is less than minimum expected %s",
            len(elements),
            min_num_elements,
        )
        return []
    elif max_num_elements is not None and len(elements) > max_num_elements:
        logger.warn(
            "Number of elements %s is greater than maximum expected %s",
            len(elements),
            max_num_elements,
        )
        return []
    return elements


def get_new_elements(scraper, current_date, dynamodb_table):
    """Return the new elements found by a scraper. An element is considered
    old, and thus skipped, if an item with key (url, id) already exists in DynamoDB"""
    elements = get_elements(scraper)
    new_elements = []
    start = timer()
    for element in elements:
        try:
            dynamodb_table.put_item(
                Item={
                    "url": scraper["url"],
                    "created_at": current_date,
                    **element,
                },
                ConditionExpression=boto3.dynamodb.conditions.Attr(
                    "url"
                ).not_exists()
                and boto3.dynamodb.conditions.Attr("id").not_exists(),
            )
            new_elements.append(element)
        except dynamodb_table.meta.client.exceptions.ConditionalCheckFailedException:
            logger.debug(
                "Item with url '%s' and id '%s' already exists in the DynamoDB table",
                scraper["url"],
                element["id"],
            )
    end = timer()
    logger.debug(
        "Took %s seconds to query DynamoDB for '%s' elements",
        end - start,
        len(elements),
    )
    logger.info("%s new elements found", len(new_elements))
    return new_elements


def get_valid_scrapers(scrapers):
    """Return a list of valid scrapers"""
    valid_scrapers = []
    for scraper in scrapers:
        if "id" in list(map(lambda attr: attr["name"], scraper["attributes"])):
            valid_scrapers.append(scraper)
        else:
            logger.warn(
                "Skipping scraper with URL '%s' as the 'id' attribute is missing",
                scraper["url"],
            )
    return valid_scrapers


def lambda_handler(event, context):
    # Enable debug logging for 10% of executions
    debug_logging = random.random() < 0.1
    if debug_logging:
        logger.info("Enabling debug logging")
        logger.setLevel(logging.DEBUG)
    dynamodb_table_name = os.environ["DYNAMODB_TABLE_NAME"]
    sns_topic_arn = os.environ["SNS_TOPIC_ARN"]
    dynamodb = boto3.resource("dynamodb")
    dynamodb_table = dynamodb.Table(dynamodb_table_name)
    sns = boto3.resource("sns")
    sns_topic = sns.Topic(sns_topic_arn)

    sns_client = boto3.client("sns")
    topic_info = sns_client.get_topic_attributes(TopicArn=sns_topic_arn)
    logger.info("Information about SNS topic '%s'", topic_info)
    if int(topic_info["Attributes"]["SubscriptionsConfirmed"]) == 0:
        if int(topic_info["Attributes"]["SubscriptionsPending"]) == 0:
            logger.info("Subscribing '%s' to SNS topic", event["notify_email"])
            sns_topic.subscribe(
                Protocol="email", Endpoint=event["notify_email"]
            )
        logger.warn("SNS topic has no subscriptions, quitting")
        return

    timestamp = datetime.now().isoformat()
    scraper_results = []
    with PoolExecutor(max_workers=4) as executor:
        for res in executor.map(
            lambda scraper: {
                **scraper,
                "new_elements": get_new_elements(
                    scraper, timestamp, dynamodb_table
                ),
            },
            event["scrapers"],
        ):
            scraper_results.append(res)
    body = get_email_body(scraper_results)
    if len(body):
        logger.info("Publishing message '%s'", body)
        sns_topic.publish(
            Subject="New elements found by scraper 🤖", Message=body
        )
    else:
        logger.info("No messages to publish")
