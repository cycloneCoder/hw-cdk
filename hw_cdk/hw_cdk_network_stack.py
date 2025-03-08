import os.path

from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
)

from constructs import Construct

class HwCdkNetworkStack(Stack):

    # Expose the VPC via the property
    @property
    def vpc(self):
        return self.hw_cdk_vpc
    
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create a VPC with:
        #   1 public and 1 private subnet in one AZ
        #   1 public and 1 private subet in another AZ
        #   Notes: 
        #       - CDK automatically assigns subnet cidr blocks, so they do not have to be explicitly declared
        #       - CDK by default creates and attaches internet gateway for VPC

        self.hw_cdk_vpc = ec2.Vpc(self, "hw_cdk_vpc",
                                  ip_addresses=ec2.IpAddresses.cidr("10.0.0.0/16"),
                                  subnet_configuration = [
                                      ec2.SubnetConfiguration(
                                        name = "PublicSubnet",
                                        subnet_type=ec2.SubnetType.PUBLIC
                                        ),
                                      ec2.SubnetConfiguration(
                                          name = "PrivateSubnet",
                                          subnet_type = ec2.SubnetType.PRIVATE_WITH_EGRESS
                                        )
                                    ],
                                  max_azs = 2
        )
