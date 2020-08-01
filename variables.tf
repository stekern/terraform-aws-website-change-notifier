variable "schedule_expression" {
  description = "The schedule expression (in Greenwich Mean Time) to use for the CloudWatch Event Rule that triggers the Lambda."
  default     = "cron(0 11 ? * MON-SUN *)"

}

variable "lambda_input" {
  description = "JSON describing the websites and elements to be scraped."
  type        = string
}

variable "name_prefix" {
  description = "A prefix to use when naming resources."
  type        = string
}
