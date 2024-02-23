from pydantic import BaseModel
from bingqilin.extras.aws.conf.types import ARN
from tests.common import BaseTestCase

from unittest import TestCase

TestCase.assertRaises


class TestARN(BaseTestCase):
    def test_simple_arn(self):
        value = "arn:aws:sns:us-east-1:123456789012:example-sns-topic-name"
        arn = ARN(value)
        self.assertEqual(arn.partition, "aws")
        self.assertEqual(arn.service, "sns")
        self.assertEqual(arn.region, "us-east-1")
        self.assertEqual(arn.account_id, "123456789012")
        self.assertNone(arn.resource_type)
        self.assertEqual(arn.resource_id, "example-sns-topic-name")
        self.assertEqual(str(arn), value)

    def test_arn_with_path(self):
        value = "arn:aws:ec2:us-east-1:123456789012:vpc/vpc-0e9801d129EXAMPLE"
        arn = ARN(value)
        self.assertEqual(arn.partition, "aws")
        self.assertEqual(arn.service, "ec2")
        self.assertEqual(arn.region, "us-east-1")
        self.assertEqual(arn.account_id, "123456789012")
        self.assertEqual(arn.resource_type, "vpc")
        self.assertEqual(arn.resource_id, "vpc-0e9801d129EXAMPLE")
        self.assertEqual(arn.resource_id_is_path, True)
        self.assertEqual(str(arn), value)

    def test_arn_with_empty_region(self):
        # IAM ARNs aren't associated with any one region
        value = "arn:aws:iam::123456789012:user/johndoe"
        arn = ARN(value)
        self.assertEqual(arn.partition, "aws")
        self.assertEqual(arn.service, "iam")
        self.assertNone(arn.region)
        self.assertEqual(arn.account_id, "123456789012")
        self.assertEqual(arn.resource_type, "user")
        self.assertEqual(arn.resource_id, "johndoe")
        self.assertEqual(arn.resource_id_is_path, True)
        self.assertEqual(str(arn), value)

    def test_arn_with_empty_region_and_acccount_id(self):
        # S3 ARNs do not have a region nor an account ID
        value = "arn:aws:s3:::the-great-bucket/path/to/a/document.json"
        arn = ARN(value)
        self.assertEqual(arn.partition, "aws")
        self.assertEqual(arn.service, "s3")
        self.assertNone(arn.region)
        self.assertNone(arn.account_id)
        self.assertEqual(arn.resource_type, "the-great-bucket")
        self.assertEqual(arn.resource_id, "path/to/a/document.json")
        self.assertEqual(arn.resource_id_is_path, True)
        self.assertEqual(str(arn), value)

    def test_arn_type_in_pydantic_model(self):
        value = "arn:aws:ssm:us-west-2:123456789012:parameter/ONE_OF_THE_PARAMETERS"

        class MyModel(BaseModel):
            some_resource: ARN

        MyModel(some_resource=value)
