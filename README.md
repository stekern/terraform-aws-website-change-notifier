# terraform-aws-website-change-notifier
A Terraform module that creates a Lambda function that periodically scrapes a set of websites, checks if new HTML elements have appeared based on XPaths, and notifies a specified email if any new elements were found.

## Configuration
The main configuration happens through the Terraform variable `lambda_input` which takes a JSON object containing information about the email address to notify, websites to scrape, which HTML elements to look for, optional formatting, and more.

An example of a configuration that finds recent song releases is shown here:
```json
{
  "notify_email": "<email-address>",
  "scrapers": [
    {
      "url": "https://www.beatport.com/releases/all?per-page=100",
      "element_xpath": "//ul[contains(@class, 'bucket-items') and contains(@class, 'ec-bucket')]/li",
      "min_num_elements": 100,
      "max_num_elements": 100,
      "attributes": [
        {
          "name": "id",
          "required": true,
          "xpath": "./@data-ec-id"
        },
        {
          "name": "title",
          "required": true,
          "xpath": ".//p[@class='buk-horz-release-title']/a/text()"
        },
        {
          "name": "artist",
          "required": true,
          "xpath": ".//p[@class='buk-horz-release-artists']/a/text()"
        }
      ]
    }
  ]
}

```


