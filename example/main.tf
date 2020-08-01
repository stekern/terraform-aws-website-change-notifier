provider "aws" {
  region = "eu-west-1"
}

module "scraper" {
  name_prefix  = "example"
  source       = "../"
  lambda_input = file("minimal.json")
}
