# terraform-aws-website-change-notifier
A Terraform module that creates a Lambda function that periodically scrapes a set of websites, checks if new HTML elements have appeared based on XPaths, and notifies a specified email if any new elements were found.

All new elements that are found are saved in DynamoDB with a primary key based on (`url`, `id`), where `url` is the URL of the scraped website and `id` is a unique identificator for a given element (e.g., track ID, item URL, etc.).

See [example](example/) for an example of a full configuration of the module.

## Configuration
The main configuration happens through the Terraform variable `lambda_input` which takes a JSON object containing information about the email address to notify, websites to scrape, which HTML elements to look for, optional formatting, and more.

It is convenient to experiment with and verify XPaths in your browser before adding them to the configuration. In Chrome and Firefox this can be done by opening the Developer Console and using the command `$x('<xpath>')`.
