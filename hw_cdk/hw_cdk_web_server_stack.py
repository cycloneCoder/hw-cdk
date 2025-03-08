import os.path

from aws_cdk.aws_s3_assets import Asset as S3asset

import aws_cdk.aws_rds as rds

from aws_cdk import (
    # Duration,
    Stack,
    aws_ec2 as ec2,
    aws_iam as iam
    # aws_sqs as sqs,
)

from constructs import Construct

dirname = os.path.dirname(__file__)
        
class HwCdkWebServerStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, hw_cdk_vpc: ec2.Vpc, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # The code that defines your stack goes here
        
        # Security group for the web servers (port 80 from anywhere)
        self.webserverSG = ec2.SecurityGroup(self, "WebserverSG",
                                        vpc = hw_cdk_vpc)
        self.webserverSG.add_ingress_rule(ec2.Peer.any_ipv4(), ec2.Port.tcp(80), "Allows HTTP")
        
        # Security group for the rds database (opens port 3306 to webserverSG)
        self.rdsSG = ec2.SecurityGroup(self, "RdsSG",
                                       vpc = hw_cdk_vpc)
        self.rdsSG.add_ingress_rule(self.webserverSG, ec2.Port.tcp(3306))
        
        # Instance Role and SSM Managed Policy
        InstanceRole = iam.Role(self, "InstanceSSM", assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"))

        InstanceRole.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSSMManagedInstanceCore"))
        
        # Launch one web server in each of the public subnets
        public_subnets = hw_cdk_vpc.select_subnets(subnet_type=ec2.SubnetType.PUBLIC).subnets
        for i, subnet in enumerate(public_subnets):
            ec2.Instance(self, f"hw_cdk_web_instance_{i+1}", vpc=hw_cdk_vpc,
                         instance_type=ec2.InstanceType("t2.micro"),
                          machine_image=ec2.AmazonLinuxImage(generation=ec2.AmazonLinuxGeneration.AMAZON_LINUX_2),
                          vpc_subnets=ec2.SubnetSelection(subnets=[subnet]),
                          role=InstanceRole,
                          security_group=self.webserverSG)
        
        # Delete this instance when deploying again!
        hw_cdk_web_instance = ec2.Instance(self, "hw_cdk_web_instance", vpc = hw_cdk_vpc,
                                           instance_type = ec2.InstanceType("t2.micro"),
                                           machine_image=ec2.AmazonLinuxImage(generation=ec2.AmazonLinuxGeneration.AMAZON_LINUX_2),
                                           vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
                                           role=InstanceRole)
        # Delete this instance when deploying again!
        
        
        # Script in S3 as Asset
        webinitscriptasset = S3asset(self, "Asset", path=os.path.join(dirname, "configure.sh"))
        asset_path = hw_cdk_web_instance.user_data.add_s3_download_command(
            bucket=webinitscriptasset.bucket,
            bucket_key=webinitscriptasset.s3_object_key
        )
        
        # Userdata executes script from S3
        hw_cdk_web_instance.user_data.add_execute_file_command(
            file_path=asset_path
            )
        webinitscriptasset.grant_read(hw_cdk_web_instance.role)
        
        # An RDS instance with MySQL engine with all private subnets as its subnet group
        hw_cdk_rds_database = rds.DatabaseInstance(self, "hw_cdk_rds_instance",
                                                   engine=rds.DatabaseInstanceEngine.mysql(version=rds.MysqlEngineVersion.VER_8_0),
                                                   instance_type=ec2.InstanceType.of(ec2.InstanceClass.BURSTABLE3, ec2.InstanceSize.SMALL),
                                                   vpc = hw_cdk_vpc,
                                                   vpc_subnets=ec2.SubnetSelection(
                                                       subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
                                                   security_group=self.rdsSG
                                                   )
        
        # Allow inbound HTTP traffic in security groups
        hw_cdk_web_instance.connections.allow_from_any_ipv4(ec2.Port.tcp(80))
        hw_cdk_rds_database.connections.add_security_group(self.rdsSG)
