data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

locals {
  current_account_id = data.aws_caller_identity.current.account_id
  current_region     = data.aws_region.current.name
}

resource "null_resource" "lambda_package" {
  triggers = {
    source       = base64sha256(file("${path.module}/src/main.py"))
    requirements = base64sha256(file("${path.module}/src/requirements-cloud.txt"))
  }
  provisioner "local-exec" {
    command     = "rm -rf ./package/* && pip install -r requirements-cloud.txt -t ./package && cp ./main.py ./package"
    working_dir = "${path.module}/src"
  }
}

data "null_data_source" "wait_for_lambda_package" {
  inputs = {
    # Wait for null_resource
    wait_id = "${null_resource.lambda_package.id}"
    # Make archive_file depend on current resource
    source_dir = "${path.module}/src/package"
  }
}

data "archive_file" "this" {
  type        = "zip"
  source_dir  = data.null_data_source.wait_for_lambda_package.outputs.source_dir
  output_path = "${path.module}/src/package.zip"
}

resource "aws_dynamodb_table" "this" {
  name         = "${var.name_prefix}-website-elements"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "url"
  range_key    = "id"

  attribute {
    name = "url"
    type = "S"
  }

  attribute {
    name = "id"
    type = "S"
  }
}

resource "aws_lambda_function" "this" {
  function_name    = "${var.name_prefix}-website-element-scraper"
  handler          = "main.lambda_handler"
  role             = aws_iam_role.this.arn
  runtime          = "python3.7"
  filename         = data.archive_file.this.output_path
  source_code_hash = data.archive_file.this.output_base64sha256
  environment {
    variables = {
      DYNAMODB_TABLE_NAME = aws_dynamodb_table.this.name
      SNS_TOPIC_ARN       = aws_sns_topic.this.arn
    }
  }
  timeout = 60
}


resource "aws_lambda_permission" "this" {
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.this.arn
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.this.arn
}

resource "aws_iam_role" "this" {
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
}

resource "aws_iam_role_policy" "logs_to_lambda" {
  policy = data.aws_iam_policy_document.logs_for_lambda.json
  role   = aws_iam_role.this.id
}

resource "aws_iam_role_policy" "sns_to_lambda" {
  policy = data.aws_iam_policy_document.sns_for_lambda.json
  role   = aws_iam_role.this.id
}

resource "aws_iam_role_policy" "dynamodb_to_lambda" {
  policy = data.aws_iam_policy_document.dynamodb_for_lambda.json
  role   = aws_iam_role.this.id
}

resource "aws_cloudwatch_event_rule" "this" {
  # TODO: Hard-coded time based on GMT
  schedule_expression = "cron(0 11 ? * MON-SUN *)"
  description         = "Scrape websites daily at 1 pm"
}

resource "aws_cloudwatch_event_target" "this" {
  rule  = aws_cloudwatch_event_rule.this.id
  arn   = aws_lambda_function.this.arn
  input = var.lambda_input
}

resource "aws_sns_topic" "this" {}
