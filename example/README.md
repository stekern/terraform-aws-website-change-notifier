# Example
This folder contains a full example on how to set up and use the module. You can edit `main.tf` to use one of the two configurations supplied here.

## Configurations
The configuration in `minimal.json` is set up to find the top releases on a music website and send you an email if any new songs have appeared since the Lambda function last ran. The configuration in `advanced.json` extends `minimal.json` by adding email formatting, exclusion patterns and mechanisms to avoid false positives.

## Step-by-step guide
1. Run `terraform apply`.
1. Update `notify_email` in the JSON configuration files.
2. Manually invoke the Lambda (`$ aws lambda invoke --function-name "example-website-element-scraper" --payload file://minimal.json output.json``)
3. You'll get an email from AWS, click **Confirm subscription**
4. (Wait roughly 30 seconds for the subscription to be confirmed), and invoke the Lambda one more time.
5. You should now have received a new email containing containing the new elements found.

By default the Lambda is automatically invoked daily at 1pm GMT. If you want to update which configuration these automated runs use, update `main.tf` accordingly.
