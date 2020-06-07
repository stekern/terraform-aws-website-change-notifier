variable "lambda_input" {
  description = "JSON describing the websites and elements to be scraped."
  type        = string
}

variable "name_prefix" {
  description = "A prefix to use when naming resources."
  type        = string
}
